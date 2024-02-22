from piexpchair import PiExpChair

import subprocess
import os


class VideoPlayer(PiExpChair):
    def __init__(self):
        super().__init__()

        self.videoplayer_process = None
        self.current_scene_index = None

    # VideoPlayer control functions
    def play(self):
        if self.videoplayer_process is not None:
            self.logger.debug("Found running player. Terminating it.")
            self.videoplayer_process.terminate()

        if self.current_scene_index >= len(self.config.scenes):
            self.logger.debug("Reached end of scenes list. Resetting pointer.")
            self.current_scene_index = None

        if isinstance(self.current_scene_index, type(None)):
            self.logger.debug("No scene pointer found. Starting at the top.")
            self.current_scene_index = 0
        else:
            self.logger.debug("Increasing scene pointer.")
            self.current_scene_index += 1

        current_scene = self.config.scenes[self.current_scene_index]
        current_file = os.path.join(self.config['videoplayer']['media_path'], current_scene['file'])

        self.logger.debug(f"Publishing scene {current_scene['name']} to MQTT")
        self.mqtt_client.publish("%s/videoplayer/scene" % self.config['mqtt']['base_topic'], current_scene['name'])

        self.logger.debug(f"Playing video file {os.path.abspath(current_file)}")
        self.videoplayer_process = subprocess.Popen(["cvlc", "--fullscreen", current_file])

    def stop(self):
        self.logger.debug("Publishing no scene playing to MQTT")
        self.mqtt_client.publish("%s/videoplayer/scene" % self.config['mqtt']['base_topic'], "")

        if self.videoplayer_process is not None:
            self.current_scene_index = None
            self.videoplayer_process.terminate()
            self.videoplayer_process = None


# Example usage
if __name__ == "__main__":
    video_player = VideoPlayer()
    video_player.run()
