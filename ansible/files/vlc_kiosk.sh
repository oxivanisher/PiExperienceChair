#!/bin/bash

/usr/bin/vlc --fullscreen --no-video-title-show --quiet-synchro --no-qt-fs-controller --disable-screensaver -I oldrc --rc-unix /tmp/vlc_rc.sock
