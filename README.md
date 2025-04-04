# PiExperienceChair

This project controls a ~~omxplayer~~ vlc and i2c outputs from a webui and some i2c button inputs.

## Ansible based automated setup
There is an ansible playbook to install and setup everything. Run the following commands as user `pi` and enter your password when asked:
```bash
sudo apt install ansible
git clone https://github.com/oxivanisher/PiExperienceChair.git
cd PiExperienceChair/ansible
ansible-playbook -i localhost install.yml --ask-become-pass
```

## Tool notes
* Check if i2c is working: `apt install i2c-tools` and `i2cdetect -y 1`
* Allow the pi user to access the i2c bus: `usermod -a -G i2c pi` (is done by the ansible setup)
* Debug MQTT issues by watching the log of `mosquitto`: `tail -f /var/log/mosquitto/mosquitto.log`

## Setup notes (all of that is done by the ansible setup)
* If the `RPi.GPIO` lib needs to be installed in a venv, you need the `python3-dev` os package.
* Remember to enable i2c in `sudo raspi-config`.
* To use a local mqtt broker you can use `mosquitto`: `apt install mosquitto`

## Idle animation notes
How to create a idle animation video from a picture:
```bash
convert "some_image.jpg_or.png" -verbose -resize 1920x1080 -background white -gravity center -extent 1920x1080 "/tmp/image_1.jpg"
ffmpeg -y -framerate "0.01" -i "/tmp/image_%d.jpg" -c:v libx264 -r 5 -pix_fmt yuv420p -preset veryslow -tune stillimage idle.mp4
```
## Get video duration
You can use ffprobe to get the exact duration of a video like this:
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 yourvideo.mp4
```

## Resources
* Some inspiration for VLC: https://github.com/m1tk4/vlc-kiosk/blob/main/vlc-kiosk
* This repository is redistributing bootstrap since it's build to be run without internet. Thanks https://getbootstrap.com <3

## File based triggers
Watchdog service events can be triggered by creating files in `tmp/`. This is mainly done, so that the unprivileged user can trigger events with root permissions.
* `force_restart`: Restart all services and VLC
* `vlc_debug`: Let VLC log to `/tmp/vlc.log` (a force_restart is required)
* `reboot_computer`: Reboot the computer
* `shutdown_computer`: Shuts the computer down


## tmp claude prompt save
#todo

I need to add support for external displays that show synchronized videos using a custom TCP protocol. I have a PDF with the protocol specifications that I'd like to implement in a similar style to the existing components.
Can you help me create a display controller that:
1. Follows the same pattern as other controllers
2. Integrates with the timed output system
3. Handles TCP communication according to the protocol
4. Synchronizes video playback with the main system

the protocol is specified in tmp/TU Series Control Protocol V3.0.0 minimized.pdf