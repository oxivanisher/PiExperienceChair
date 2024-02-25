import time

from piexpchair import PiExpChair

import os
import socket

class VideoPlayer(PiExpChair):
    def __init__(self):
        super().__init__()

        # self.videoplayer_process = None
        self.current_scene_index = 0

        # self.vlc_url = f"http://{self.config['videoplayer']['rc_host']}:{self.config['videoplayer']['rc_port']}/requests/"
        self.start_videoplayer()
        self.load_idle_animation()

    def start_videoplayer(self):
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

        self.send_vlc_command("clear")
        self.send_vlc_command("add " + current_file)
        for scene in self.config['scenes']:
            current_file = os.path.join(self.config['videoplayer']['media_path'],
                                        scene['file'])
            self.send_vlc_command("add " + current_file)
        self.send_vlc_command("goto 1")
        self.send_vlc_command("repeat on")
        self.send_vlc_command("play")

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
    def play_scene(self):
        if self.current_scene_index >= len(self.config['scenes']):
            self.logger.debug("Reached end of scenes list. Back to the idle animation.")
            self.load_idle_animation()

        self.logger.debug(f"Play scene pointer: {self.current_scene_index}")

        playlist_position = self.current_scene_index + 1

        current_scene = self.config['scenes'][self.current_scene_index]
        current_file = os.path.join(self.config['videoplayer']['media_path'], current_scene['file'])

        self.logger.debug(f"Publishing scene {current_scene['name']} to MQTT")
        self.mqtt_client.publish("%s/videoplayer/scene" % self.config['mqtt']['base_topic'], self.current_scene_index)

        self.logger.debug(f"Playing video file {os.path.abspath(current_file)} for scene {current_scene['name']}")
        self.send_vlc_command("repeat off")
        self.send_vlc_command("goto %d" % playlist_position)
        self.send_vlc_command("play")

    def play(self):
        self.logger.info("Received play request (starting at the top)")
        self.current_scene_index = 0
        self.play_scene()

    def next(self):
        self.logger.info("Received next request")
        self.current_scene_index += 1
        self.play_scene()

    def prev(self):
        self.logger.info("Received prev request")
        self.current_scene_index -= 1
        if self.current_scene_index < 0:
            self.current_scene_index = 0
        self.play_scene()

    def stop(self):
        self.logger.info("Received stop request")
        self.load_idle_animation()

    def quit(self):
        self.logger.info("Received quit request")
        self.stop_videoplayer()


# Example usage
if __name__ == "__main__":
    video_player = VideoPlayer()
    video_player.run()
