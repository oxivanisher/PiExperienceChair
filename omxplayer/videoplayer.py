import subprocess
import json
import paho.mqtt.client as mqtt

from tools import read_config

config = read_config('config/config.yaml')

# Initialize OMXPlayer subprocess
omxplayer_process = None

# Initialize MQTT client
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)


# OMXPlayer control functions
def play_video(video_file):
    global omxplayer_process
    if omxplayer_process is not None:
        stop_video()
    omxplayer_process = subprocess.Popen(["omxplayer", "--no-osd", video_file])


def stop_video():
    global omxplayer_process
    if omxplayer_process is not None:
        omxplayer_process.terminate()
        omxplayer_process = None


# MQTT callback functions
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code "+str(rc))
    # Subscribe to control topic
    mqtt_client.subscribe("%s/control" % config['mqtt']['base_topic'])


def on_message(client, userdata, msg):
    print("Received message on topic "+msg.topic+": "+msg.payload.decode())
    try:
        payload = json.loads(msg.payload.decode())
        command = payload.get("command")
        if command == "play":
            video_file = payload.get("video_file")
            if video_file:
                play_video(video_file)
        elif command == "stop":
            stop_video()
        else:
            print("Invalid command:", command)
    except Exception as e:
        print("Error processing message:", e)


# Configure MQTT client callbacks
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# Connect to MQTT broker
mqtt_client.connect(config['mqtt']['host'], config['mqtt']['port'])

# Start MQTT loop
mqtt_client.loop_forever()
