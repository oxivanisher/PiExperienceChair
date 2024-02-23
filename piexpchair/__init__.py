import yaml
import logging
import os
import random
import time

import paho.mqtt.client as mqtt
from paho.mqtt.enums import MQTTProtocolVersion

CONFIG_PATH = os.getenv('CONFIG_PATH', "config/config.yaml")

log_level = logging.INFO
if os.getenv('DEBUG', False):
    log_level = logging.DEBUG

logging.basicConfig(
    format='%(asctime)s %(levelname)-7s %(message)s',
    datefmt='%Y-%d-%m %H:%M:%S',
    level=log_level
)


def read_config(file_path):
    try:
        with open(file_path, 'r') as file:
            config_data = yaml.safe_load(file)
        return config_data
    except FileNotFoundError:
        print(f"Config file '{file_path}' not found.")
        return None
    except yaml.YAMLError as e:
        print(f"Error reading config file '{file_path}': {e}")
        return None


class PiExpChair:
    def __init__(self):
        self.logger = logging

        self.logger.info(f"Initializing PiExpChair module {self.__class__.__name__}")

        self.logger.debug(f"Loading config from {os.path.abspath(CONFIG_PATH)}")
        self.config = read_config('config/config.yaml')

        # Initialize MQTT client
        self.mqtt_client_id = f'PiExpChair-{self.__class__.__name__}-{random.randint(0, 1000)}'

        self.logger.debug(f"Connecting to MQTT broker with client ID: {self.mqtt_client_id}")
        self.mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                                       client_id=self.mqtt_client_id,
                                       protocol=MQTTProtocolVersion.MQTTv5)

        if log_level == logging.DEBUG:
            self.logger.debug(f"Enable MQTT logging since DEBUG is enabled")
            self.mqtt_client.enable_logger(self.logger)

        # Configure MQTT client callbacks
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

        # Connect to MQTT broker
        self.mqtt_client.will_set("%s/status" % self.config['mqtt']['base_topic'],
                                  f"{self.mqtt_client_id} offline", 0, False)
        self.mqtt_client.connect(self.config['mqtt']['host'], self.config['mqtt']['port'])

        self.terminate = False

    # MQTT callback functions
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            self.logger.warning(f"Failed to connect, return code: {reason_code}")
            return False
        else:
            self.logger.debug("Successfully connected to MQTT Broker")
            self.mqtt_subscribe(client, "control")

            self.mqtt_client.publish("%s/status" % self.config['mqtt']['base_topic'],
                                     f"{self.mqtt_client_id} online")
            return True

    def on_message(self, client, userdata, msg):
        try:
            self.logger.debug(f"Received message on topic {msg.topic}: {msg.payload}")
            if msg.topic == "%s/control" % self.config['mqtt']['base_topic']:
                if msg.payload.decode() == "quit":
                    self.logger.info("Received quit command")
                    self.quit()
                elif msg.payload.decode() == "play":
                    self.logger.info("Received play command")
                    self.play()
                elif msg.payload.decode() == "stop":
                    self.logger.info("Received stop command")
                    self.stop()
                elif msg.payload.decode() == "next":
                    self.logger.info("Received next command")
                    self.next()
                elif msg.payload.decode() == "prev":
                    self.logger.info("Received prev command")
                    self.prev()
        except Exception as e:
            self.logger.warning("Error processing message in on_message:", e)

    def mqtt_subscribe(self, client, channel_name):
        channel = "%s/%s" % (self.config['mqtt']['base_topic'], channel_name)
        self.logger.debug(f"Subscribing to channel: {channel}")
        client.subscribe(channel)

    def _send_control_command(self, command):
        self.mqtt_client.publish("%s/control" % self.config['mqtt']['base_topic'], command)

    def send_quit(self):
        self.logger.info("Sending quit command")
        self._send_control_command("quit")

    def send_play(self):
        self.logger.info("Sending play command")
        self._send_control_command("play")

    def send_stop(self):
        self.logger.info("Sending stop command")
        self._send_control_command("stop")

    def send_next(self):
        self.logger.info("Sending next command")
        self._send_control_command("next")

    def send_prev(self):
        self.logger.info("Sending prev command")
        self._send_control_command("prev")

    # Player methods
    def play(self):
        self.logger.debug("Method play not implemented")

    def stop(self):
        self.logger.debug("Method stop not implemented")

    def next(self):
        self.logger.debug("Method next not implemented")

    def prev(self):
        self.logger.debug("Method prev not implemented")

    # Control methods
    def run(self):
        self.logger.debug("Entering main loop")
        while not self.terminate:
            try:
                self.mqtt_client.loop_start()
                # time.sleep(0.05)
                # self.mqtt_client.loop_misc()
            except Exception as e:
                self.logger.warning("Error processing message in main loop:", e)
        self.logger.debug("Main loop ended")
        self.mqtt_client.disconnect()

    def quit(self):
        self.logger.debug("Terminating main loop")
        self.terminate = True
