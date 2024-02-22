from piexpchair import PiExpChair

from mcp23017 import *
from smbus2 import SMBus


class MCP23017Controller(PiExpChair):
    def __init__(self):
        super().__init__()

        # self.i2c = busio.I2C(board.SCL, board.SDA)
        # self.mcp = adafruit_mcp230xx.MCP23017(self.i2c)

        # https://github.com/sensorberg/MCP23017-python
        with SMBus(1) as bus:
            self.mcp = MCP23017(0x27, bus)  # creates an MCP object with the given address

        self.i2c_inputs = {}
        for input_name in self.config['i2c']['input'].keys():
            self.logger.debug(f"Configure input button for {input_name}")
            # do i2c stuff with self.config['i2c']['input'][input_name]['address']
            # and self.config['i2c']['input'][input_name]['pin']
            # and save it in self.i2c_inputs[input_name]
            # also register the outputs to self.play/... methods

        self.i2c_outputs = []
        for output_name in self.config['i2c']['output'].keys():
            self.logger.debug(f"Configure output {output_name}")
            # do i2c stuff with self.config['i2c']['output'][input_name]['address']
            # and self.config['i2c']['output'][input_name]['pin']
            # and save it in self.i2c_outputs[output_name]

    # # MQTT callback functions
    def mqtt_subscribe(self):
        super().mqtt_subscribe()

        self.logger.debug("Subscribing to videoplayer channel")
        self.mqtt_client.subscribe("%s/videoplayer" % self.config['mqtt']['base_topic'])

    def on_message(self, client, userdata, msg):
        super().on_message(client, userdata, msg)

        try:
            if msg.topic == "%s/videoplayer" % self.config['mqtt']['base_topic']:

                if msg.payload.decode() == "":
                    self.logger.info("Received play no scene command")
                elif isinstance(msg.payload.decode(), int):
                    self.logger.info(f"Received scene index {msg.payload.decode()} to play")
                    self.play_scene(msg.payload.decode())
                else:
                    self.logger.info(f"Received unknown scene command: {msg.payload.decode()}")
        except Exception as e:
            self.logger.warning("Error processing message in on_message for videoplayer:", e)

    def play_scene(self, scene_index):
        current_scene = self.config.scenes[scene_index]
        self.logger.Info(f"Playing scene {current_scene['name']}")
        for output_name in current_scene['i2c_outputs']:
            if output_name not in self.i2c_outputs.keys():
                self.logger.warning(f"Scene {current_scene['name']} wants to control unknown output: {output_name}")
            else:
                self.set_output(output_name, current_scene['i2c_outputs'][output_name])

    def set_output(self, output_name, state):
        self.logger.debug(f"Setting output {output_name} to state: {state}")
        if state:
            self.mcp.output_pins[relay_num].value = True
        else:
            self.mcp.output_pins[relay_num].value = False


# Example usage
if __name__ == "__main__":
    mcp_controller = MCP23017Controller()
    mcp_controller.run()
