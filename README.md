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

## Deployment
* ssh as pi into the raspberry pi
* git clone https://github.com/oxivanisher/PiExperienceChair.git
* python3 -m venv /home/pi/.local
* /home/pi/.local/bin/pip install -r PiExperienceChair/requirements.txt
* sudo cp PiExperienceChair/dist/piexpchair_i2c.service /etc/systemd/system/
* sudo cp PiExperienceChair/dist/piexpchair_videoplayer.service /etc/systemd/system/
* sudo cp PiExperienceChair/dist/piexpchair_webui.service /etc/systemd/system/
* sudo systemctl daemon-reload
* sudo systemctl enable --now piexpchair_i2c.service
* sudo systemctl enable --now piexpchair_videoplayer.service
* sudo systemctl enable --now piexpchair_webui.service
* VLC in user desktop hes to be documented yet...

## Idle animation notes
How to create a idle animation video from a picture:
```bash
convert "some_image.jpg_or.png" -verbose -resize 1920x1080 -background black -gravity center -extent 1920x1080 "/tmp/image_1.jpg"
ffmpeg -y -framerate "0.01" -i "/tmp/image_%d.jpg" -c:v libx264 -r 30 -pix_fmt yuvj444p -preset veryslow -tune stillimage idle.mp4
```

## Resources
* https://github.com/m1tk4/vlc-kiosk/blob/main/vlc-kiosk
