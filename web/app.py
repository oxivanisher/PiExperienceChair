from flask import Flask, request
import json
import paho.mqtt.client as mqtt

from tools import read_config

app = Flask(__name__)

config = read_config('config/config.yaml')

# Initialize MQTT client
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)


# Helper methods
def send_control_command(command):
    mqtt_client.publish("%s/control" % config['mqtt']['base_topic'], json.dumps({"command": command}))


# Routes for controlling OMXPlayer
@app.route('/play')
def play():
    send_control_command("play")
    return "OK"


@app.route('/stop')
def stop():
    send_control_command("stop")
    return "OK"


# Routes for managing YAML configuration file
@app.route('/config')
def get_config():
    # Read YAML configuration file and return it as JSON
    # Example implementation:
    with open('config/config.yaml', 'r') as file:
        config_data = json.load(file)
    return json.dumps(config_data)


@app.route('/config', methods=['POST'])
def update_config():
    # Update YAML configuration file based on POST request data
    # Example implementation:
    new_config = request.json
    with open('config/config.yaml', 'w') as file:
        json.dump(new_config, file)
    return "OK"


# MQTT callback functions
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code "+str(rc))
    # Subscribe to status topic
    mqtt_client.subscribe("%s/status" % config['mqtt']['base_topic'])


def on_message(client, userdata, msg):
    print("Received message on topic "+msg.topic+": "+msg.payload.decode())


# Configure MQTT client callbacks
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# Connect to MQTT broker
mqtt_client.connect(config['mqtt']['host'], config['mqtt']['port'])

if __name__ == '__main__':
    app.run(debug=True)  # Set debug=True for development
