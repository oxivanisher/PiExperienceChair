import yaml
import logging
import os
import random
import time

from schema import Schema, And, Use, Optional, SchemaError
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

broker_schema = Schema({"host": str, "port": int, "base_topic": str})

config_schema = Schema({
    "videoplayer": {"media_path": str, "rc_socket": str, "idle_animation": str},
    "i2c": {"input": {"play": {"address": hex, "pin": int},
                      "stop": {"address": hex, "pin": int},
                      "next": {"address": hex, "pin": int},
                      "prev": {"address": hex, "pin": int},
                      "shutdown": {"address": hex, "pin": int}},
            "output": {str: {"address": hex, "pin": int}}},
    "scenes": [{"name": str, "file": str, "i2c_outputs": {str: bool}, "duration": float}]
})


def check_config_for_webui():
    try:
        with open('config/config.yaml', 'r') as file:
            config_data = yaml.safe_load(file)
    except FileNotFoundError:
        return False, "Config file 'config/config.yaml' not found."
    except yaml.YAMLError as e:
        return False, f"Error reading config file 'config/config.yaml': {e}"

    try:
        config_schema.validate(config_data)
        return True, "Config seems to be valid!"
    except SchemaError as se:
        return False, se


def read_config(file_path, logger, schema_config):
    try:
        with open(file_path, 'r') as file:
            config_data = yaml.safe_load(file)
    except FileNotFoundError:
        logger.error(f"Config file '{file_path}' not found.")
        return None
    except yaml.YAMLError as e:
        logger.error(f"Error reading config file '{file_path}': {e}")
        return None

    try:
        schema_config.validate(config_data)
        logger.debug("Valid config file found")
        return config_data
    except SchemaError as se:
        logger.error(se)
        return None


class PiExpChair:
    def __init__(self, subscribe_to_everything=False):
        self.logger = logging

        self.logger.info(f"Initializing PiExpChair module {self.__class__.__name__}")

        self.logger.debug(f"Loading config from {os.path.abspath(CONFIG_PATH)}")

        self.mqtt_config = read_config('config/broker.yaml', self.logger, broker_schema)

        self.config = read_config('config/config.yaml', self.logger, config_schema)

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
        self.mqtt_client.will_set("%s/status" % self.mqtt_config['base_topic'],
                                  f"{self.mqtt_client_id} offline", 0, False)
        self.mqtt_client.connect(self.mqtt_config['host'], self.mqtt_config['port'])

        self.last_messages = {}
        self.subscribe_to_everything = subscribe_to_everything

        if self.config:
            self.terminate = False
        else:
            self.terminate = True

    # MQTT helper methods
    def log_mqtt_message(self, msg):
        if msg.topic not in self.last_messages.keys():
            self.last_messages[msg.topic] = {}
        self.last_messages[msg.topic][time.time()] = msg.payload
        if len(self.last_messages[msg.topic]) > 10:
            self.last_messages[msg.topic].pop(list(self.last_messages[msg.topic].keys())[0], None)

    # MQTT callback methods
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            self.logger.warning(f"Failed to connect, return code: {reason_code}")
            return False
        else:
            self.logger.debug("Successfully connected to MQTT Broker")
            self.mqtt_subscribe(client, "control")

            if self.subscribe_to_everything:
                self.mqtt_subscribe(client, "videoplayer/#")
                self.mqtt_subscribe(client, "i2c/#")


            self.mqtt_client.publish("%s/status" % self.mqtt_config['base_topic'],
                                     f"{self.mqtt_client_id} online")
            return True

    def on_message(self, client, userdata, msg):
        try:
            self.logger.debug(f"Received message on topic {msg.topic}: {msg.payload}")
            self.log_mqtt_message(msg)

            if msg.topic == "%s/control" % self.mqtt_config['base_topic']:
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
                elif msg.payload.decode() == "shutdown":
                    self.logger.info("Received shutdown command")
                    self.shutdown()
        except Exception as e:
            self.logger.warning("Error processing message in on_message:", e)

    def mqtt_subscribe(self, client, channel_name):
        channel = "%s/%s" % (self.mqtt_config['base_topic'], channel_name)
        self.logger.debug(f"Subscribing to channel: {channel}")
        client.subscribe(channel)

    def _send_control_command(self, command):
        self.mqtt_client.publish("%s/control" % self.mqtt_config['base_topic'], command)

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

    def send_reboot(self):
        self.logger.info("Sending reboot command")
        self._send_control_command("reboot")

    def send_shutdown(self):
        self.logger.info("Sending shutdown command")
        self._send_control_command("shutdown")

    # Player methods
    def play(self):
        self.logger.debug("Method play not implemented")

    def stop(self):
        self.logger.debug("Method stop not implemented")

    def next(self):
        self.logger.debug("Method next not implemented")

    def prev(self):
        self.logger.debug("Method prev not implemented")

    def shutdown(self):
        self.logger.debug("Method shutdown not implemented")

    # Control methods
    def module_run(self):
        pass

    def run(self):
        if self.terminate:
            self.logger.warning("NOT Entering main loop, probably invalid config found. Exiting")
        else:
            self.logger.debug("Entering main loop")

            try:
                self.mqtt_client.loop_start()

                while not self.terminate:
                    self.module_run()
                    time.sleep(0.01)

            except Exception as e:
                self.logger.warning("Error processing message in main loop:", e)
            finally:
                self.mqtt_client.loop_stop()
                self.logger.debug("Main loop ended")
                self.mqtt_client.disconnect()

    def quit(self):
        self.logger.debug("Terminating main loop")
        self.terminate = True
