from piexpchair import PiExpChair
import json
import time


class WLEDController(PiExpChair):
    def __init__(self):
        super().__init__()

        if self.terminate:
            return

        self.mqtt_path_identifier = "wled"
        self.wled_transistion = 20
        if 'wled' in self.config and 'settings' in self.config['wled']:
            if 'transition' in self.config['wled']['settings'].keys():
                self.wled_transistion = self.config['wled']['settings']['transition']

        # Initialize WLED devices from config
        self.wled_devices = []
        if 'wled' in self.config and 'devices' in self.config['wled']:
            self.wled_devices = self.config['wled']['devices']
            self.logger.debug(f"Registered the following WLED device: {', '.join(self.wled_devices)}")

        self.wled_macros = {}
        if 'wled' in self.config and 'macros' in self.config['wled']:
            self.wled_macros = self.config['wled']['macros']

        self.wled_colors = {}
        if 'wled' in self.config and 'colors' in self.config['wled']:
            self.wled_colors = self.config['wled']['colors']

    def apply_scene_outputs(self, current_outputs):
        if 'wled_outputs' in current_outputs:
            for device in self.wled_devices:
                device_output = {"on": True, "transition": self.wled_transistion, "seg": []}
                for strip, macro_name in current_outputs['wled_outputs'].items():
                    macro = self.wled_macros[macro_name]
                    colors = self.wled_colors[macro['color']]
                    strip_output = {"id": strip, "on": macro['strip_on'], "bri": macro['brightness'],
                                    "fx": macro['effect_id'], "sx": macro['speed'], "ix": macro['intensity'],
                                    "tt": self.wled_transistion, "transition": self.wled_transistion,
                                    "col": colors, "pal": 0}
                    device_output['seg'].append(strip_output)
                    self.logger.debug(f"WLED should to set strip {strip} to macro {macro}")

                self.logger.debug(f"Sending WLED command over MQTT for {device}")
                self.mqtt_client.publish(f"wled/{device}/api", json.dumps(device_output))

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
    wled_controller = WLEDController()
    wled_controller.run()