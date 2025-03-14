from piexpchair import PiExpChair

import socket
import struct
import time

"""
# Step 1: Initialize Program List
init_program_list_cmd = bytes.fromhex("55AA0001FC000800000000000C00000001005E56")
response = send_command(init_program_list_cmd)

# Extract the number of programs (last byte of response before checksum)
num_programs = response[-3] if len(response) > 3 else 0
print(f"Total Programs: {num_programs}")

# Step 2: Play the first program (Modify '0201' to select another program)
play_program_cmd = bytes.fromhex("55AA0001FC000800000001000C000000020002015E56")
send_command(play_program_cmd)

# Step 3: Example additional controls
pause_cmd = bytes.fromhex("55AA0001FC000800000001000C0000000100035E56")
resume_cmd = bytes.fromhex("55AA0001FC000800000001000C0000000100045E56")
exit_cmd = bytes.fromhex("55AA0001FC000800000001000C0000000100055E56")

# Uncomment to use playback controls:
# send_command(pause_cmd)   # Pause playback
# send_command(resume_cmd)  # Resume playback
# send_command(exit_cmd)    # Exit current playback
"""
CONNECT_COMMAND = "aa55000000fe0000000000000200000002000a218256"

class NovastarController(PiExpChair):
    def __init__(self):
        super().__init__()

        if self.terminate:
            return


        # test_cmd = bytes.fromhex("55AA0001FC000000000000002A00000001007D56")  # Example test command
        # response = self.send_command(test_cmd)
        # print(f"Test Response: {response.hex()}")
        #
        # status_cmd = bytes.fromhex("55AA0001FC000800000000000C00000001005E56")  # Init list command
        # response = self.send_command(status_cmd)
        # self.logger.debug(f"Status Response: {response.hex()}")
        #
        # # Step 1: Initialize Program List
        # init_program_list_cmd = bytes.fromhex("55AA0001FC000800000000000C00000001005E56")
        # response = self.send_command(init_program_list_cmd)
        #
        # # Extract the number of programs (last byte of response before checksum)
        # num_programs = response[-3] if len(response) > 3 else 0
        # self.logger.debug(f"Total Programs found: {num_programs}")

    # Helper function to send commands
    def calculate_checksum(self, data):
        """Calculates the checksum by summing all bytes and adding 0x5555."""
        checksum = sum(data) + 0x5555
        return checksum & 0xFFFF  # Ensure it's 2 bytes

    def build_play_command(self, file_index):
        """Builds the correct TCP command to play a specific video by index."""
        command_base = bytes.fromhex("55AA0001FC000800000001000C00000002")

        # Convert index to bytes (e.g., 1 -> 0x0201, 2 -> 0x0202)
        file_index_bytes = struct.pack(">H", file_index)  # Big-endian format

        # Construct full command (excluding checksum for now)
        command = command_base + file_index_bytes

        # Calculate checksum
        checksum = self.calculate_checksum(command)
        self.logger.debug(f"Calculated Checksum: {checksum:04X}")  # Log as hex

        # Append checksum as 2 bytes
        command += struct.pack(">H", checksum)

        return command

    def send_command(self, command):
        """Sends a TCP command to the TU15 Pro."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)  # 5 seconds timeout
            self.logger.debug(
                f"Connecting to {self.config['novastar']['controller_ip']}:{self.config['novastar']['controller_port']}")
            try:
                s.connect((self.config['novastar']['controller_ip'], self.config['novastar']['controller_port']))
            except socket.timeout:
                self.logger.error("Connection timed out!")
                return None
            except socket.error as e:
                self.logger.error(f"Socket error: {e}")
                return None

            self.logger.debug(f"Sending connect command: {bytes.fromhex(CONNECT_COMMAND)}")
            try:
                s.sendall(bytes.fromhex(CONNECT_COMMAND))
                self.logger.debug(f"Waiting for response")
                response = b""
                while True:
                    chunk = s.recv(1024)
                    if not chunk:
                        break
                    response += chunk
                self.logger.debug(f"Connect response: {response.hex()}")

                self.logger.debug(f"Sending command: {command}")
                s.sendall(command)
                self.logger.debug(f"Waiting for response")
                response = b""
                while True:
                    chunk = s.recv(1024)
                    if not chunk:
                        break
                    response += chunk
                self.logger.debug(f"Full Response: {response.hex()}")
            except socket.timeout:
                self.logger.warning("Connection timed out!")

            return response

    def play_video(self, file_index):
        """Plays a specific video based on its index."""
        command = self.build_play_command(file_index)
        response = self.send_command(command)
        return response

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