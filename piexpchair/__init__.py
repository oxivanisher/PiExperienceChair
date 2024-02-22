import yaml
import logging
import os
import random

import paho.mqtt.client as mqtt

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

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.logger.debug("Successfully connected to MQTT Broker")
            else:
                self.logger.warning("Failed to connect, return code %d\n", rc)

        self.logger.debug(f"Connecting to MQTT broker with client ID: {self.mqtt_client_id}")
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, self.mqtt_client_id)

        if log_level == logging.DEBUG:
            self.logger.debug(f"Enable MQTT logging")
            self.mqtt_client.enable_logger()

        # Configure MQTT client callbacks
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_subscribe()

        # Connect to MQTT broker
        self.mqtt_client.will_set("%s/status" % self.config['mqtt']['base_topic'],
                                  f"{self.mqtt_client_id} offline", 0, False)
        self.mqtt_client.connect(self.config['mqtt']['host'], self.config['mqtt']['port'])
        self.mqtt_client.loop_start()

        self.mqtt_client.publish("%s/status" % self.config['mqtt']['base_topic'],
                                 f"{self.mqtt_client_id} online")

        self.terminate = False

    # MQTT callback functions
    def mqtt_subscribe(self):
        self.logger.debug("Subscribing to control channel")
        self.mqtt_client.subscribe("%s/control" % self.config['mqtt']['base_topic'])

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
        self.logger.debug("Method play implemented")

    def stop(self):
        self.logger.debug("Method stop implemented")

    def next(self):
        self.logger.debug("Method next implemented")

    def prev(self):
        self.logger.debug("Method prev implemented")

    # Control methods
    def run(self):
        self.logger.debug("Entering main loop")
        while not self.terminate:
            try:
                self.mqtt_client.loop(.05)
            except Exception as e:
                self.logger.warning("Error processing message in main loop:", e)
        self.logger.debug("Main loop ended")
        self.mqtt_client.disconnect()

    def quit(self):
        self.logger.debug("Terminating main loop")
        self.terminate = True
