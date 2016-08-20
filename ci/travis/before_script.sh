#!/usr/bin/env bash

if [ $TRAVIS_OS_NAME == "linux" ]
then
    #export XVFBARGS=":99 -screen 0 1280x1024x24 +extension RANDR +extension RENDER +extension GLX"
    #export DISPLAY=:99.0
    #sudo chmod a+x /etc/init.d/xvfb
    #sudo sh -e /etc/init.d/xvfb restart
    sudo sh -e /etc/init.d/xvfb stop
    Xvfb :10 -screen 0 1280x960x24 +extension RANDR +extension RENDER +extension GLX &
    sleep 3
fi
