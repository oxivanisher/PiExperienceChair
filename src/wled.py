from piexpchair import PiExpChair
import json


class WLEDController(PiExpChair):
    def __init__(self):
        super().__init__(identifier="wled")

        if self.terminate:
            return

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
                    self.output_notify(f"{device}/{strip}/bri",  macro['brightness'])

                self.logger.debug(f"Sending WLED command over MQTT for {device}")
                self.mqtt_client.publish(f"wled/{device}/api", json.dumps(device_output))

    def output_set(self, name, value):
        device, strip, element = name.split("/")
        self.logger.info(f"Setting {element} on strip {strip} and device {device} to {value}")
        device_output = {"on": True, "transition": self.wled_transistion, "seg": [{"id": strip, element: value}]}
        self.mqtt_client.publish(f"wled/{device}/api", json.dumps(device_output))
        self.output_notify(f"{device}/{strip}/{element}", value)

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
    wled_controller = WLEDController()
    wled_controller.run()