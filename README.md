# PiExperienceChair

This project controls a ~~omxplayer~~ vlc and i2c outputs from a webui and some i2c button inputs.

## Setup notes
* If the `RPi.GPIO` lib needs to be installed in a venv, you need the `python3-dev` os package. 
* Remember to enable i2c in `sudo raspi-config`.
* To use a local mqtt broker you can use `mosquitto`: `apt install mosquitto`
* Debug MQTT issues by watching the log of `mosquitto`: `tail -f /var/log/mosquitto/mosquitto.log`


## Tool notes
* Check if i2c is working: `apt install i2c-tools` and `i2cdetect -y 1`
* Allow the pi user to access the i2c bus: `usermod -a -G i2c pi`

## Resources
* https://github.com/m1tk4/vlc-kiosk/blob/main/vlc-kiosk