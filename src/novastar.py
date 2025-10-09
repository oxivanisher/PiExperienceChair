from piexpchair import PiExpChair

import socket
import select

class NovastarController(PiExpChair):
    def __init__(self):
        super().__init__(identifier="novastar")

        if self.terminate:
            return

        self.logger.info(f"Initialize program list on Novastar controller: {self.config['novastar']['controller_ip']}:{self.config['novastar']['controller_port']}")
        if not self.send_command("55AA0001FC000800000001000C000000020002055E56"):
            self.logger.error("Failed to initialize program list, unable to connect to Novastar controller. Exiting.")
            self.terminate = True

    def build_play_command(self, file_index):
        return f"55AA0001FC000800000001000C000000020002{file_index:02x}5E56"

    def send_command(self, command):
        binary_data = bytes.fromhex(command)

        try:
            with socket.create_connection((self.config['novastar']['controller_ip'], int(self.config['novastar']['controller_port'])), timeout=1) as s:
                self.logger.debug(
                    f"Connecting to {self.config['novastar']['controller_ip']}:{self.config['novastar']['controller_port']}")

                self.logger.debug(f"Sending command: {command}")
                s.sendall(binary_data)
                s.settimeout(3)  # Set a timeout for recv
                self.logger.debug(f"Waiting for response")
                response = b""
                while True:
                    ready, _, _ = select.select([s], [], [], 1)
                    if not ready:
                        break

                    chunk = s.recv(1024)
                    if not chunk:
                        break
                    response += chunk
                self.logger.info(f"Received the response from the Novastar Controller: {response.hex()}")
                return True

        except socket.timeout:
            self.logger.error("Connection timed out!")
            return False
        except socket.error as e:
            self.logger.error(f"Socket error: {e}")
            return False

    def play_video(self, file_index):
        if not self.send_command(self.build_play_command(file_index)):
            self.logger.warning(f"Failed to play video index {file_index}!")
        self.output_notify("video_index", file_index)

    def output_set(self, name, value):
        self.logger.info(f"Setting {name} to {value}")
        if name ==  "video_index":
            self.play_video(value)

    def apply_scene_outputs(self, current_outputs):
        if 'novastar_output' in current_outputs:
            self.logger.info(f"Playing novastar video: {current_outputs['novastar_output']}")
            self.play_video(current_outputs['novastar_output'])

    def on_connect(self, client, userdata, flags, reason_code, properties):
        super().on_connect(client, userdata, flags, reason_code, properties)
        self.mqtt_subscribe(client, "videoplayer/#")

    def on_message(self, client, userdata, msg):
        super().on_message(client, userdata, msg)

        try:
            if msg.topic == f"{self.mqtt_config['base_topic']}/videoplayer/scene":

                if msg.payload.decode() == "":
                    self.logger.info("Received play no scene command")
                else:
                    self.current_scene_index = int(msg.payload.decode())
                    if 0 <= self.current_scene_index < len(self.config['scenes']):
                        self.logger.info(f"Received scene index {self.current_scene_index} to play")
                        self.play_scene(True)
                        self.mqtt_client.publish(f"{self.mqtt_config['base_topic']}/{self.mqtt_path_identifier}/scene", self.current_scene_index)
                    else:
                        self.logger.info(f"Received unknown scene index: {msg.payload.decode()}")

            elif msg.topic == f"{self.mqtt_config['base_topic']}/videoplayer/idle":
                self.logger.info("Received idle scene command")
                self.mqtt_client.publish(f"{self.mqtt_config['base_topic']}/{self.mqtt_path_identifier}/idle", True)
                self.set_idle_outputs()

        except Exception as e:
            self.logger.warning("Error processing message in on_message for videoplayer:", e)

    def play_scene(self, scene_index):
        # Reset output magic
        self.check_for_output_change(start=True)

    def module_run(self):
        self.handle_output_change()


# Example usage
if __name__ == "__main__":
    wled_controller = NovastarController()
    wled_controller.run()