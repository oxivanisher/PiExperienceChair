import board
import busio

# import adafruit_mcp230xx
from mcp23017 import *
from i2c import I2C
import smbus

import json
import paho.mqtt.client as mqtt

from tools import read_config

# https://github.com/sensorberg/MCP23017-python
i2c = I2C(smbus.SMBus(1))  # creates a I2C Object as a wrapper for the SMBus
mcp = MCP23017(0x20, i2c)   # creates an MCP object with the given address

config = read_config('config/config.yaml')


class MCP23017Controller:
    def __init__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.mcp = adafruit_mcp230xx.MCP23017(self.i2c)

        # Initialize MQTT client
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

        # Configure MQTT client callbacks
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

        # Connect to MQTT broker
        self.mqtt_client.connect(config['mqtt']['host'], config['mqtt']['port'])
        self.mqtt_client.loop_start()

    # MQTT callback functions
    def on_connect(self, client, userdata, flags, rc):
        print("Connected to MQTT broker with result code "+str(rc))
        # Subscribe to control topic
        self.mqtt_client.subscribe("%s/control" % config['mqtt']['base_topic'])

    def on_message(self, client, userdata, msg):
        print("Received message on topic "+msg.topic+": "+msg.payload.decode())
        try:
            payload = json.loads(msg.payload.decode())
            command = payload.get("command")
            if command == "control_relay":
                relay_num = payload.get("relay_num")
                state = payload.get("state")
                if relay_num is not None and state is not None:
                    self.control_relay(relay_num, state)
                else:
                    print("Missing parameters for control_relay command")
            else:
                print("Invalid command:", command)
        except Exception as e:
            print("Error processing message:", e)

    def control_relay(self, relay_num, state):
        if state:
            self.mcp.output_pins[relay_num].value = True
        else:
            self.mcp.output_pins[relay_num].value = False


# Example usage
if __name__ == "__main__":
    mcp_controller = MCP23017Controller()

    # Test controlling relay
    mcp_controller.control_relay(0, True)  # Turn on relay 0
