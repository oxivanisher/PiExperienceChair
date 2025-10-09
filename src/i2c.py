from piexpchair import PiExpChair

import board
import busio
import digitalio
import struct
import time
from adafruit_mcp230xx.mcp23017 import MCP23017

i2c = busio.I2C(board.SCL, board.SDA)


class I2cController(PiExpChair):
    def __init__(self):
        super().__init__()

        if self.terminate:
            return

        self.mqtt_path_identifier = "i2c"

        # find all i2c addresses (MCP23017)
        i2c_addresses = []
        for key in self.config['i2c']['input']:
            i2c_addresses.append(self.config['i2c']['input'][key]['address'])
        for key in self.config['i2c']['output']:
            i2c_addresses.append(self.config['i2c']['output'][key]['address'])
        i2c_addresses = list(set(i2c_addresses))
        self.logger.debug(f"Found MCP23017 i2c addresses (as int) in config: {i2c_addresses}")

        # Get Arduino addresses if configured
        self.arduino_devices = {}
        if 'arduino_devices' in self.config['i2c']:
            for device_name, device_config in self.config['i2c']['arduino_devices'].items():
                self.arduino_devices[device_name] = device_config
                self.logger.debug(
                    f"Found Arduino device {device_name} in config at address: {hex(device_config['address'])}")

        self.mcp = {}
        self.input_states = {}

        for addr in i2c_addresses:
            self.logger.debug(f"Setup mcp for i2c address: {hex(addr)}")
            self.mcp[addr] = MCP23017(i2c, addr)  # creates an MCP object with the given address

        self.i2c_inputs = {}
        for input_name in self.config['i2c']['input'].keys():
            self.logger.debug(f"Configure input button for {input_name}")
            input = self.config['i2c']['input'][input_name]
            self.i2c_inputs[input_name] = self.mcp[input['address']].get_pin(input['pin'])
            self.i2c_inputs[input_name].direction = digitalio.Direction.INPUT
            self.i2c_inputs[input_name].direction = digitalio.Direction.INPUT
            self.i2c_inputs[input_name].pull = digitalio.Pull.UP
            self.input_states[input_name] = True

        self.i2c_outputs = {}
        for output_name in self.config['i2c']['output'].keys():
            self.logger.debug(f"Configure output {output_name}")
            output = self.config['i2c']['output'][output_name]
            self.i2c_outputs[output_name] = self.mcp[output['address']].get_pin(output['pin'])
            self.i2c_outputs[output_name].direction = digitalio.Direction.OUTPUT

        # Disable all outputs at startup
        self.set_idle_outputs()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        super().on_connect(client, userdata, flags, reason_code, properties)
        self.mqtt_subscribe(client, "videoplayer/#")

    def on_message(self, client, userdata, msg):
        super().on_message(client, userdata, msg)

        try:
            if msg.topic == f"{self.mqtt_config['base_topic']}/videoplayer/scene":

                if msg.payload.decode() == "":
                    self.logger.info("Received play no scene command")
                else:
                    self.current_scene_index = int(msg.payload.decode())
                    if 0 <= self.current_scene_index < len(self.config['scenes']):
                        self.logger.info(f"Received scene index {self.current_scene_index} to play")
                        self.play_scene(True)
                        self.mqtt_client.publish(f"{self.mqtt_config['base_topic']}/{self.mqtt_path_identifier}/scene", self.current_scene_index)
                    else:
                        self.logger.info(f"Received unknown scene index: {msg.payload.decode()}")

            elif msg.topic == f"{self.mqtt_config['base_topic']}/videoplayer/idle":
                self.logger.info("Received idle scene command")
                self.mqtt_client.publish(f"{self.mqtt_config['base_topic']}/{self.mqtt_path_identifier}/idle", True)
                self.set_idle_outputs()

        except Exception as e:
            self.logger.warning("Error processing message in on_message for videoplayer:", e)

    def play_scene(self, scene_index):
        # Reset output magic
        self.check_for_output_change(start=True)

    def apply_scene_outputs(self, current_outputs):
        if 'i2c_outputs' in current_outputs:
            for output_name, state in current_outputs['i2c_outputs'].items():
                self.set_i2c_output(output_name, state)
        if 'arduino_outputs' in current_outputs:
            for device_name, value in current_outputs['arduino_outputs'].items():
                self.set_arduino_output(device_name, value)

    def set_i2c_output(self, output_name, state):
        self.logger.debug(f"Setting output {output_name} to state: {state}")
        if output_name in self.i2c_outputs:
            self.i2c_outputs[output_name].value = bool(state)
        else:
            self.logger.warning(f"Unknown output: {output_name}")

    def send_arduino_command(self, address, output_pin, value):
        """
        Send command to Arduino device using the custom protocol
        :param address: i2c Address
        :param output_pin: Output pin number (0-255)
        :param value: Value to set (0-255)
        """
        try:

            # Pack two bytes as struct
            data = struct.pack('BB', output_pin, value)

            # Write the data to the I2C bus
            while not i2c.try_lock():
                pass

            i2c.writeto(address, data)

            self.logger.debug(f"Sent command to Arduino {address}: pin={output_pin}, value={value}")
        except Exception as e:
            self.logger.warning(f"Error sending command to Arduino at address {address}: {e}")

        finally:
            i2c.unlock()

    def set_arduino_output(self, device_name, value):
        """
        Set an Arduino output to a specific value
        :param device_name: Name of the Arduino device from config
        :param value: Value to set (0-255 for PWM, 0 or 1 for digital)
        """
        if device_name not in self.arduino_devices.keys():
            self.logger.warning(f"Unknown Arduino device: {device_name}")
            return

        device = self.arduino_devices[device_name]

        # Ensure value is in valid range
        value = max(0, min(255, int(value)))

        self.send_arduino_command(device['address'], device['pin'], value)

    def module_run(self):
        self.handle_output_change()
        for input_name in self.i2c_inputs.keys():
            try:
                current_value = self.i2c_inputs[input_name].value
                if current_value != self.input_states[input_name]:
                    self.logger.debug(f"Input {input_name} changed to {current_value}")
                    self.input_states[input_name] = current_value
                    if not current_value:
                        if input_name == "play":
                            self.logger.debug("Detected play button press")
                            self.send_play()
                        elif input_name == "stop":
                            self.logger.debug("Detected stop button press")
                            self.send_stop()
                        elif input_name == "next":
                            self.logger.debug("Detected next button press")
                            self.send_next()
                        elif input_name == "prev":
                            self.logger.debug("Detected prev button press")
                            self.send_prev()
                        elif input_name == "shutdown":
                            self.logger.debug("Detected shutdown button press")
                            self.send_shutdown()
                            with open("tmp/shutdown_computer", "w") as text_file:
                                text_file.write(f"Force system shutdown from i2c at {time.time()}")
            except OSError as e:
                self.logger.warning(f"Catching OSError during reading of the pins: {e}")

    def stop(self):
        self.logger.info("Received stop request. Disabling all outputs.")
        self.set_idle_outputs()

    def shutdown(self):
        self.logger.info("Received shutdown request. Disabling all outputs.")
        self.set_idle_outputs()

# Example usage
if __name__ == "__main__":
    mcp_controller = I2cController()
    mcp_controller.run()