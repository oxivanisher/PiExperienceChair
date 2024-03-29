from piexpchair import PiExpChair

import board
import busio
import digitalio
from adafruit_mcp230xx.mcp23017 import MCP23017

i2c = busio.I2C(board.SCL, board.SDA)


class MCP23017Controller(PiExpChair):
    def __init__(self):
        super().__init__()

        if self.terminate:
            return

        # find all i2c addresses:
        i2c_addresses = []
        for key in self.config['i2c']['input']:
            i2c_addresses.append(self.config['i2c']['input'][key]['address'])
        for key in self.config['i2c']['output']:
            i2c_addresses.append(self.config['i2c']['output'][key]['address'])
        i2c_addresses = list(set(i2c_addresses))
        self.logger.debug(f"Detected i2c addresses (as int): {i2c_addresses}")

        self.mcp = {}
        self.input_states = {}

        for addr in i2c_addresses:
            self.logger.debug(f"Register mcp for i2c address: {hex(addr)}")
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
        self.disable_outputs()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        super().on_connect(client, userdata, flags, reason_code, properties)
        self.mqtt_subscribe(client, "videoplayer/#")

    # # MQTT callback functions
    def on_message(self, client, userdata, msg):
        super().on_message(client, userdata, msg)

        try:
            if msg.topic == "%s/videoplayer/scene" % self.mqtt_config['base_topic']:

                if msg.payload.decode() == "":
                    self.logger.info("Received play no scene command")
                else:
                    scene_index = int(msg.payload.decode())
                    if 0 <= scene_index < len(self.config['scenes']):
                        self.logger.info(f"Received scene index {scene_index} to play")
                        self.play_scene(scene_index)
                        self.mqtt_client.publish("%s/i2c/scene" % self.mqtt_config['base_topic'], scene_index)
                    else:
                        self.logger.info(f"Received unknown scene index: {msg.payload.decode()}")

            elif msg.topic == "%s/videoplayer/idle" % self.mqtt_config['base_topic']:
                self.logger.info("Received idle scene command")
                self.mqtt_client.publish("%s/i2c/idle" % self.mqtt_config['base_topic'], "idle")
                self.disable_outputs()

        except Exception as e:
            self.logger.warning("Error processing message in on_message for videoplayer:", e)

    def play_scene(self, scene_index):
        current_scene = self.config['scenes'][scene_index]
        self.logger.info(f"Playing scene {current_scene['name']}")
        for output_name in current_scene['i2c_outputs']:
            if output_name not in self.config['i2c']['output'].keys():
                self.logger.warning(f"Scene {current_scene['name']} wants to control unknown output: {output_name}")
            else:
                self.set_output(output_name, current_scene['i2c_outputs'][output_name])

    def set_output(self, output_name, state):
        self.logger.debug(f"Setting output {output_name} to state: {state}")
        if state:
            self.i2c_outputs[output_name].value = True
        else:
            self.i2c_outputs[output_name].value = False

    def module_run(self):
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
                                text_file.write("Force system shutdown from i2c at %s" % time.time())
            except OSError as e:
                self.logger.warning(f"Catching OSError during reading of the pins: {e}")

    def stop(self):
        self.logger.info("Received stop request. Disabling all outputs.")
        self.disable_outputs()

    def shutdown(self):
        self.logger.info("Received shutdown request. Disabling all outputs.")
        self.disable_outputs()
    
    def disable_outputs(self):
        self.logger.debug("Disabling all outputs.")
        for output_name in self.i2c_outputs:
            self.i2c_outputs[output_name].value = False


# Example usage
if __name__ == "__main__":
    mcp_controller = MCP23017Controller()
    mcp_controller.run()
