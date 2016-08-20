#!/usr/bin/env bash

if [ $TRAVIS_OS_NAME == "linux" ]
then
    export XVFBARGS="-screen 0 1280x1024x24"
    export DISPLAY=:99.0
    sudo chmod a+x /etc/init.d/xvfb
    sudo sh -e /etc/init.d/xvfb restart
    sleep 3
fi
