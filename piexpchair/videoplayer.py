import time

from piexpchair import PiExpChair

import subprocess
import os
import requests
import urllib.parse


class VideoPlayer(PiExpChair):
    def __init__(self):
        super().__init__()

        self.videoplayer_process = None
        self.current_scene_index = -1

        self.vlc_url = f"http://{self.config['videoplayer']['rc_host']}:{self.config['videoplayer']['rc_port']}/requests/"
        self.start_videoplayer()

    def start_videoplayer(self):
        self.logger.info("Starting video player")
        self.videoplayer_process = subprocess.Popen(["cvlc", "--fullscreen", "--no-video-title-show", "--quiet-synchro",
                                                     "--no-qt-fs-controller", "--disable-screensaver", "--intf", "http",
                                                     "--http-host", str(self.config['videoplayer']['rc_host']),
                                                     "--http-port", str(self.config['videoplayer']['rc_port']),
                                                     "--http-password", str(self.config['videoplayer']['rc_password'])])

    def stop_videoplayer(self):
        self.logger.info("Stopping video player")
        # self.videoplayer_socket.close()
        self.videoplayer_process.terminate()
        self.videoplayer_process = None

    def send_vlc_command_play(self, file_name):
        self.logger.debug("Sending vlc play file: " + file_name)
        safe_url = "".join([self.vlc_url, "?command=in_play&input=", urllib.parse.quote_plus(file_name)])
        self.logger.debug(f"Requests url: {safe_url}")
        response = requests.get(safe_url, auth=('', self.config['videoplayer']['rc_password']))
        self.logger.debug(f"Sending vlc command result: {response.status_code}")

    # VideoPlayer control functions
    def play(self):
        if self.videoplayer_process is not None:
            self.logger.debug("Found running player. Terminating it.")
            self.videoplayer_process.terminate()

        if self.current_scene_index >= len(self.config['scenes']):
            self.logger.debug("Reached end of scenes list. Resetting pointer.")
            self.current_scene_index = -1

        if isinstance(self.current_scene_index, type(None)):
            self.logger.debug("No scene pointer found. Starting at the top.")
            self.current_scene_index = 0
        else:
            self.logger.debug("Increasing scene pointer.")
            self.current_scene_index += 1

        current_scene = self.config['scenes'][self.current_scene_index]
        current_file = os.path.join(self.config['videoplayer']['media_path'], current_scene['file'])

        self.logger.debug(f"Publishing scene {current_scene['name']} to MQTT")
        self.mqtt_client.publish("%s/videoplayer/scene" % self.config['mqtt']['base_topic'], current_scene['name'])

        self.logger.debug(f"Playing video file {os.path.abspath(current_file)}")
        self.send_vlc_command_play(current_file)

        # self.videoplayer_process = subprocess.Popen(["cvlc", "--fullscreen", current_file])

    def stop(self):
        self.logger.debug("Publishing no scene playing to MQTT")
        self.mqtt_client.publish("%s/videoplayer/scene" % self.config['mqtt']['base_topic'], "")

        self.send_vlc_command("stop")
        # if self.videoplayer_process is not None:
        #     self.current_scene_index = None
        #     self.videoplayer_process.terminate()
        #     self.videoplayer_process = None

    def quit(self):
        self.logger.info("Received quit request")
        self.stop_videoplayer()


# Example usage
if __name__ == "__main__":
    video_player = VideoPlayer()
    video_player.run()
