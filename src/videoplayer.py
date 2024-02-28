import time

from piexpchair import PiExpChair

import os
import socket

class VideoPlayer(PiExpChair):
    def __init__(self):
        super().__init__()

        if self.terminate:
            return

        self.current_scene_index = -1
        self.next_timeout = -1.0

        self.initialize_videoplayer()
        self.load_idle_animation()


    def initialize_videoplayer(self):
        self.logger.info("Starting video player")
        vlc_command = ["vlc", "--fullscreen", "--no-video-title-show", "--quiet-synchro", "--no-qt-fs-controller",
                       "--disable-screensaver", "-I", "oldrc", "--rc-unix", self.config['videoplayer']['rc_socket']]
        self.logger.debug("Please make sure a VLC is running: %s", " ".join(vlc_command))
        self.logger.debug("List of configured scenes:")
        for idx, scene in enumerate(self.config['scenes']):
            self.logger.debug(f"{idx}: {scene['name']}")
        # note: get the interface to test commands:
        # cvlc --fullscreen --no-video-title-show --quiet-synchro --no-qt-fs-controller --disable-screensaver --extraintf rc

    def load_idle_animation(self):
        self.logger.debug(f"Loading idle animation: {self.config['videoplayer']['idle_animation']}")

        current_file = os.path.join(self.config['videoplayer']['media_path'],
                                    self.config['videoplayer']['idle_animation'])
        self.current_scene_index = -1
        self.next_timeout = -1.0

        self.send_vlc_command("clear")
        self.send_vlc_command("add " + current_file)
        self.send_vlc_command("play")
        self.send_vlc_command("repeat on")

        for scene in self.config['scenes']:
            current_file = os.path.join(self.config['videoplayer']['media_path'],
                                        scene['file'])
            self.send_vlc_command("enqueue " + current_file)
        self.mqtt_client.publish("%s/videoplayer/idle" % self.mqtt_config['base_topic'], "")

    def stop_videoplayer(self):
        self.logger.info("Stopping video player")
        self.load_idle_animation()

    def send_vlc_command(self, command):
        client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client_socket.connect(self.config['videoplayer']['rc_socket'])
            client_socket.sendall(command.encode())
        except FileNotFoundError:
            self.logger.warning(f"VLC control socket in {self.config['videoplayer']['rc_socket']} not found. "
                                f"Is VLC running?")

        finally:
            client_socket.close()

    # VideoPlayer control functions
    def play_scene(self, scene_index):
        if scene_index >= len(self.config['scenes']):
            self.logger.debug("Reached end of scenes list. Back to the idle animation.")
            self.load_idle_animation()
        elif scene_index < 0:
            self.logger.debug("Reached beginning of scenes list. Back to the idle animation.")
            self.load_idle_animation()
        else:
            self.current_scene_index = scene_index
            playlist_position = self.current_scene_index + 2

            self.logger.debug(f"Play python scene: {self.current_scene_index} (vlc playlist index: {playlist_position})")

            current_scene = self.config['scenes'][self.current_scene_index]
            current_file = os.path.join(self.config['videoplayer']['media_path'], current_scene['file'])
            self.next_timeout = time.time() + current_scene['duration']

            self.logger.debug(f"Publishing scene {current_scene['name']} to MQTT")
            self.mqtt_client.publish("%s/videoplayer/scene" % self.mqtt_config['base_topic'], self.current_scene_index)

            self.logger.debug(f"Playing video file {os.path.abspath(current_file)} for scene {current_scene['name']}")
            self.send_vlc_command("goto %d" % playlist_position)
            self.send_vlc_command("play")

    def play(self):
        self.logger.info("Received play request (starting at the top)")
        self.play_scene(0)

    def next(self):
        self.logger.info("Received next request")
        next_index = self.current_scene_index + 1
        self.play_scene(next_index)

    def prev(self):
        self.logger.info("Received prev request")
        prev_index = self.current_scene_index - 1
        self.play_scene(prev_index)

    def stop(self):
        self.logger.info("Received stop request")
        self.load_idle_animation()

    def module_run(self):
        if self.next_timeout > 0:
            if time.time() >= self.next_timeout:
                self.logger.debug("Play next video callback")
                self.next_timeout = 0
                self.send_next()


# Example usage
if __name__ == "__main__":
    video_player = VideoPlayer()
    video_player.run()
