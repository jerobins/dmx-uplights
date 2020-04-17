#!/bin/bash

sleep 60

cd "$(dirname "$0")";
./dmx-mqtt.py &

exit
