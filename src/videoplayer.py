import time

from piexpchair import PiExpChair

import os
import socket


class VideoPlayer(PiExpChair):
    def __init__(self):
        super().__init__()

        if self.terminate:
            return

        self.next_scene_timeout = -1.0
        self.playback_start_time = None
        self.return_to_idle = False

        self.initialize_videoplayer()
        self.load_idle_animation()

        self.mqtt_path_identifier = "videoplayer"

    def initialize_videoplayer(self):
        self.logger.info("Starting video player")
        vlc_command = ["vlc", "--fullscreen", "--no-video-title-show", "--quiet-synchro", "--no-qt-fs-controller",
                       "--disable-screensaver", "-I", "oldrc", "--rc-unix", self.config['videoplayer']['rc_socket']]
        self.logger.debug("Please make sure a VLC is running: %s", " ".join(vlc_command))
        self.logger.debug("List of configured scenes:")
        for idx, scene in enumerate(self.config['scenes']):
            self.logger.debug(f"{idx}: {scene['name']}")

    def load_idle_animation(self):
        self.logger.debug(f"Loading idle animation: {self.config['idle']['file']}")

        current_file = os.path.join(self.config['videoplayer']['media_path'],
                                    self.config['idle']['file'])
        self.next_scene_timeout = -1.0

        self.send_vlc_command("clear")
        self.send_vlc_command("add " + current_file)
        self.send_vlc_command("play")
        self.send_vlc_command("repeat on")

        # Reset playback timing
        self.playback_start_time = None
        self.current_scene_index = -1

        for scene in self.config['scenes']:
            current_file = os.path.join(self.config['videoplayer']['media_path'],
                                        scene['file'])
            self.send_vlc_command("enqueue " + current_file)
        self.mqtt_client.publish(f"{self.mqtt_config['base_topic']}/{self.mqtt_path_identifier}/idle", "idle")

    def stop_videoplayer(self):
        self.logger.info("Stopping video player")
        self.load_idle_animation()

    def send_vlc_command(self, command):
        client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.logger.debug(f"Send VLC command: {command}")
            client_socket.connect(self.config['videoplayer']['rc_socket'])
            client_socket.sendall(command.encode())
        except FileNotFoundError:
            self.logger.warning(f"VLC control socket in {self.config['videoplayer']['rc_socket']} not found. "
                                f"Is VLC running?")

        finally:
            client_socket.close()

    def play_scene(self, scene_index):
        if scene_index >= len(self.config['scenes']):
            self.logger.info("Reached end of scenes list. Back to the idle animation.")
            self.load_idle_animation()
        elif scene_index < 0:
            self.logger.info("Reached beginning of scenes list. Starting at the beginning.")
            self.play()
        else:
            self.current_scene_index = scene_index
            playlist_position = self.current_scene_index + 2

            self.logger.debug(f"Play python scene: {self.current_scene_index} (vlc playlist index: {playlist_position})")

            current_scene = self.config['scenes'][self.current_scene_index]
            current_file = os.path.join(self.config['videoplayer']['media_path'], current_scene['file'])
            self.next_scene_timeout = time.time() + current_scene['duration']

            self.logger.debug(f"Publishing scene {current_scene['name']} to MQTT")
            self.mqtt_client.publish(f"{self.mqtt_config['base_topic']}/{self.mqtt_path_identifier}/scene", self.current_scene_index)

            self.logger.debug(f"Playing video file {os.path.abspath(current_file)} for scene {current_scene['name']}")
            self.send_vlc_command("goto %d" % playlist_position)
            self.send_vlc_command("play")

    def play_single(self, scene_index):
        if 0 <= scene_index < len(self.config['scenes']):
            self.logger.info(f"Playing single scene at index {scene_index}")
            self.play_scene(scene_index)
            # Set a flag to indicate we want to return to idle after this scene
            self.next_scene_timeout = time.time() + self.config['scenes'][scene_index]['duration']
            self.return_to_idle = True

            current_scene = self.config['scenes'][self.current_scene_index]
            current_file = os.path.join(self.config['videoplayer']['media_path'], current_scene['file'])

            self.logger.debug(f"Playing video file {os.path.abspath(current_file)} for single scene {current_scene['name']}")
            self.mqtt_client.publish(f"{self.mqtt_config['base_topic']}/{self.mqtt_path_identifier}/scene", self.current_scene_index)
        else:
            self.logger.warning(f"Invalid scene index for single play: {scene_index}")
            self.load_idle_animation()

    def play(self):
        # Start playback and set up first scene
        self.play_scene(0)
        self.return_to_idle = False

    def next(self):
        self.logger.info("Received next request")
        next_index = self.current_scene_index + 1
        if not hasattr(self, 'return_to_idle') or not self.return_to_idle:
            self.play_scene(next_index)
        else:
            self.load_idle_animation()

    def prev(self):
        self.logger.info("Received prev request")
        prev_index = self.current_scene_index - 1
        if not hasattr(self, 'return_to_idle') or not self.return_to_idle:
            self.play_scene(prev_index)
        else:
            self.load_idle_animation()

    def stop(self):
        self.logger.info("Received stop request")
        self.load_idle_animation()

    def shutdown(self):
        self.logger.info("Received shutdown request")
        self.load_idle_animation()

    def module_run(self):
        # Handle scene transitions
        if self.next_scene_timeout > 0:
            if time.time() >= self.next_scene_timeout:
                self.logger.debug("Play next video callback")
                self.next_scene_timeout = 0
                if hasattr(self, 'return_to_idle') and self.return_to_idle:
                    self.load_idle_animation()
                else:
                    self.send_next()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        super().on_connect(client, userdata, flags, reason_code, properties)
        self.mqtt_subscribe(client, f"{self.mqtt_path_identifier}/#")


# Example usage
if __name__ == "__main__":
    video_player = VideoPlayer()
    video_player.run()