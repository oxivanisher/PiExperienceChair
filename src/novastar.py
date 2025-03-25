from piexpchair import PiExpChair

import socket
import select

class NovastarController(PiExpChair):
    def __init__(self):
        super().__init__()

        if self.terminate:
            return

        self.logger.info(f"Initialize Program List on Novastar Controller: {self.config['novastar']['controller_ip']}:{self.config['novastar']['controller_port']}")
        response = self.send_command("55AA0001FC000800000001000C000000020002055E56")
        self.logger.info(f"Received the response from the Novastar Controller: {response.hex()}")

    def build_play_command(self, file_index):
        return f"55AA0001FC000800000001000C000000020002{file_index:02x}5E56"

    def send_command(self, command):
        binary_data = bytes.fromhex(command)

        with socket.create_connection((self.config['novastar']['controller_ip'], self.config['novastar']['controller_port']), timeout=3) as s:
            self.logger.debug(
                f"Connecting to {self.config['novastar']['controller_ip']}:{self.config['novastar']['controller_port']}")
            try:
                self.logger.debug(f"Sending command: {command}")
                s.sendall(binary_data)
                s.settimeout(1)  # Set a timeout for recv
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
                self.logger.debug(f"Full Response: {response.hex()}")

            except socket.timeout:
                self.logger.error("Connection timed out!")
                return None
            except socket.error as e:
                self.logger.error(f"Socket error: {e}")
                return None

            return response

    def play_video(self, file_index):
        return self.send_command(self.build_play_command(file_index))

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
            if msg.topic == "%s/videoplayer/scene" % self.mqtt_config['base_topic']:

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

            elif msg.topic == "%s/videoplayer/idle" % self.mqtt_config['base_topic']:
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