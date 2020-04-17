#!/bin/bash

sudo apt-get -y install python3-pip
sudo pip3 install configparser
sudo pip3 install paho-mqtt
sudo pip3 install simplejson
sudo pip3 install psutil

sudo cp rc.local /etc/rc.local
crontab crontab.out
