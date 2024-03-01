#!/bin/bash

while true;
do
  echo "$(date) Starting VLC"
  /usr/bin/vlc --fullscreen --no-video-title-show --quiet-synchro --no-qt-fs-controller --disable-screensaver -I oldrc --rc-unix /tmp/vlc_rc.sock
  echo "$(date) VLC ended. Restarting it in 1 second."
  sleep 1
done
