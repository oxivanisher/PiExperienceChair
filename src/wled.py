from piexpchair import PiExpChair
import json
import time


class WLEDController(PiExpChair):
    def __init__(self):
        super().__init__()

        if self.terminate:
            return

        # Initialize WLED devices from config
        self.wled_devices = {}
        if 'wled' in self.config and 'devices' in self.config['wled']:
            for device_name, device_config in self.config['wled']['devices'].items():
                self.wled_devices[device_name] = device_config
                self.logger.debug(
                    f"Registered WLED device {device_name} with topic: {device_config['topic']}")

    def set_wled_state(self, device_name, rgb=None, effect_id=None, speed=None, intensity=None):
        """
        Set WLED device state
        :param device_name: Name of the WLED device from config
        :param rgb: List of [r,g,b] values (0-255)
        :param effect_id: Effect ID number
        :param speed: Effect speed (0-255)
        :param intensity: Effect intensity (0-255)
        """
        if device_name not in self.wled_devices:
            self.logger.warning(f"Unknown WLED device: {device_name}")
            return

        device = self.wled_devices[device_name]
        state = {}

        # Only include parameters that are provided
        if rgb is not None:
            state['rgb'] = rgb
        if effect_id is not None:
            state['effect_id'] = effect_id
        if speed is not None:
            state['speed'] = speed
        if intensity is not None:
            state['intensity'] = intensity

        # Send state update via MQTT
        if state:
            self.mqtt_client.publish(
                f"{device['topic']}/api",
                json.dumps(state)
            )
            self.logger.debug(f"Sent state update to WLED device {device_name}: {state}")

    def apply_scene_outputs(self, scene_index, current_time_ms):
        """
        Apply WLED outputs for the current scene at the specified time
        :param scene_index: Index of the current scene
        :param current_time_ms: Current playback time in milliseconds
        """
        scene = self.config['scenes'][scene_index]

        if 'timed_outputs' in scene:
            # Track the latest state for each WLED device
            latest_states = {}

            # Find all outputs that should be applied at or before current_time_ms
            for output_set in scene['timed_outputs']:
                if output_set['time'] <= current_time_ms and 'wled_outputs' in output_set:
                    for device_name, state in output_set['wled_outputs'].items():
                        if device_name not in latest_states:
                            latest_states[device_name] = {}
                        # Update with the latest values, preserving any previously set values
                        latest_states[device_name].update(state)

            # Apply the final states to each device
            for device_name, state in latest_states.items():
                self.set_wled_state(
                    device_name,
                    rgb=state.get('rgb'),
                    effect_id=state.get('effect_id'),
                    speed=state.get('speed'),
                    intensity=state.get('intensity')
                )

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
                        self.apply_scene_outputs(scene_index, 0)  # Apply initial outputs
                    else:
                        self.logger.info(f"Received unknown scene index: {msg.payload.decode()}")

            elif msg.topic == "%s/videoplayer/idle" % self.mqtt_config['base_topic']:
                self.logger.info("Received idle scene command")
                self.disable_outputs()

        except Exception as e:
            self.logger.warning(f"Error processing message in on_message: {e}", exc_info=True)

    def disable_outputs(self):
        """
        Disable all WLED outputs (set to off or idle state)
        """
        self.logger.debug("Disabling all WLED outputs")
        for device_name in self.wled_devices:
            # You can customize this default/idle state
            self.set_wled_state(
                device_name,
                rgb=[0, 0, 0],  # Off
                effect_id=0,  # Solid color
                speed=128,  # Mid speed
                intensity=0  # No intensity
            )

    def module_run(self):
        super().module_run()
        """
        Main module run loop - can be used for continuous state monitoring
        """
        pass  # Add any continuous monitoring if needed


# Example usage
if __name__ == "__main__":
    wled_controller = WLEDController()
    wled_controller.run()