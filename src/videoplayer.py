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
        self.playback_start_time = None
        self.current_output_index = {}  # Track current output index for each scene

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

        # Reset playback timing
        self.playback_start_time = None
        self.current_scene_index = -1

        self.mqtt_client.publish("%s/videoplayer/idle" % self.mqtt_config['base_topic'], "idle")

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

    def play_scene(self, scene_index):
        if scene_index >= len(self.config['scenes']):
            self.logger.info("Reached end of scenes list. Back to the idle animation.")
            self.load_idle_animation()
        elif scene_index < 0:
            self.logger.info("Reached beginning of scenes list. Starting at the beginning.")
            self.play()
        else:
            self.current_scene_index = scene_index
            current_scene = self.config['scenes'][self.current_scene_index]
            current_file = os.path.join(self.config['videoplayer']['media_path'], current_scene['file'])
            self.next_timeout = time.time() + current_scene['duration']

            # Reset playback timing
            self.playback_start_time = time.time()
            self.current_output_index[scene_index] = 0

            # Add file to playlist and play it
            self.send_vlc_command("clear")
            self.send_vlc_command("add " + current_file)
            self.send_vlc_command("play")

            # Apply initial outputs
            self.apply_scene_outputs(scene_index, 0)

            self.logger.debug(f"Playing video file {os.path.abspath(current_file)} for scene {current_scene['name']}")
            self.mqtt_client.publish("%s/videoplayer/scene" % self.mqtt_config['base_topic'], self.current_scene_index)

    def apply_scene_outputs(self, scene_index, current_time_ms):
        """
        Apply outputs for the current scene at the specified time
        :param scene_index: Index of the current scene
        :param current_time_ms: Current playback time in milliseconds
        """
        scene = self.config['scenes'][scene_index]

        # Handle static outputs (backward compatibility)
        if 'i2c_outputs' in scene:
            for output_name, state in scene['i2c_outputs'].items():
                self.mqtt_client.publish(
                    f"{self.mqtt_config['base_topic']}/i2c/output/{output_name}",
                    "1" if state else "0"
                )

        # Handle timed outputs
        if 'timed_outputs' in scene:
            # Find all outputs that should be applied at or before current_time_ms
            current_states = {}  # Track latest state for each output
            arduino_states = {}  # Track latest state for each Arduino output

            for output_set in scene['timed_outputs']:
                if output_set['time'] <= current_time_ms:
                    # Update I2C outputs
                    if 'i2c_outputs' in output_set:
                        for output_name, state in output_set['i2c_outputs'].items():
                            current_states[output_name] = state

                    # Update Arduino outputs
                    if 'arduino_outputs' in output_set:
                        for device_name, outputs in output_set['arduino_outputs'].items():
                            if device_name not in arduino_states:
                                arduino_states[device_name] = {}
                            for output_name, value in outputs.items():
                                arduino_states[device_name][output_name] = value

            # Apply the final states
            for output_name, state in current_states.items():
                self.mqtt_client.publish(
                    f"{self.mqtt_config['base_topic']}/i2c/output/{output_name}",
                    "1" if state else "0"
                )

            for device_name, outputs in arduino_states.items():
                for output_name, value in outputs.items():
                    self.mqtt_client.publish(
                        f"{self.mqtt_config['base_topic']}/i2c/arduino/{device_name}/{output_name}",
                        str(value)
                    )

    def play_single_scene(self, scene_index):
        """
        Play a single scene and return to idle animation after completion
        :param scene_index: Index of the scene to play
        """
        if 0 <= scene_index < len(self.config['scenes']):
            self.logger.info(f"Playing single scene at index {scene_index}")
            self.play_scene(scene_index)
            # Set a flag to indicate we want to return to idle after this scene
            self.next_timeout = time.time() + self.config['scenes'][scene_index]['duration']
            self.return_to_idle = True
        else:
            self.logger.warning(f"Invalid scene index for single play: {scene_index}")
            self.load_idle_animation()

    def play(self):
        self.logger.info("Received play request (starting at the top)")
        # For regular play, we'll queue all scenes
        self.send_vlc_command("clear")

        # Add idle animation first (it will be replaced when first scene starts)
        idle_file = os.path.join(self.config['videoplayer']['media_path'],
                                 self.config['videoplayer']['idle_animation'])
        self.send_vlc_command("add " + idle_file)

        # Add all scenes to playlist
        for scene in self.config['scenes']:
            current_file = os.path.join(self.config['videoplayer']['media_path'], scene['file'])
            self.send_vlc_command("enqueue " + current_file)

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
        # Handle timed outputs
        if self.current_scene_index >= 0 and self.playback_start_time is not None:
            current_time = time.time()
            current_time_ms = int((current_time - self.playback_start_time) * 1000)

            # Apply outputs for current time
            self.apply_scene_outputs(self.current_scene_index, current_time_ms)

        # Handle scene transitions
        if self.next_timeout > 0:
            if time.time() >= self.next_timeout:
                self.logger.debug("Play next video callback")
                self.next_timeout = 0
                if hasattr(self, 'return_to_idle') and self.return_to_idle:
                    self.load_idle_animation()
                else:
                    self.send_next()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        super().on_connect(client, userdata, flags, reason_code, properties)
        self.mqtt_subscribe(client, "videoplayer/#")

    def on_message(self, client, userdata, msg):
        super().on_message(client, userdata, msg)

        try:
            if msg.topic == "%s/videoplayer/scene" % self.mqtt_config['base_topic']:
                if msg.payload.decode() == "":
                    self.logger.info("Received play no scene command")
                else:
                    scene_index = int(msg.payload.decode())
                    if 0 <= scene_index < len(self.config['scenes']):
                        self.logger.info(f"Received scene index {scene_index} to play")
                        self.play_scene(scene_index)
                        self.mqtt_client.publish("%s/i2c/scene" % self.mqtt_config['base_topic'], scene_index)
                    else:
                        self.logger.info(f"Received unknown scene index: {msg.payload.decode()}")

            elif msg.topic == "%s/videoplayer/play_single" % self.mqtt_config['base_topic']:
                if msg.payload.decode() != "":
                    scene_index = int(msg.payload.decode())
                    self.logger.info(f"Received single scene play request for index {scene_index}")
                    self.play_single_scene(scene_index)

            elif msg.topic == "%s/videoplayer/idle" % self.mqtt_config['base_topic']:
                self.logger.info("Received idle scene command")
                self.mqtt_client.publish("%s/i2c/idle" % self.mqtt_config['base_topic'], "idle")
                self.load_idle_animation()

        except Exception as e:
            self.logger.warning("Error processing message in on_message for videoplayer:", e)


# Example usage
if __name__ == "__main__":
    video_player = VideoPlayer()
    video_player.run()