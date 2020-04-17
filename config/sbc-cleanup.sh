#!/bin/bash

cmd="mosquitto_pub -u <userID> -P <userPass> -h <MQTTHOST> -p 1883 -r -n -t "

$cmd ha/sbc/${1}/LWT
$cmd homeassistant/sensor/$1/${1}Temp/config
$cmd homeassistant/sensor/$1/${1}DiskUse/config
$cmd homeassistant/sensor/$1/${1}MemoryUse/config
$cmd homeassistant/sensor/$1/${1}CpuUsage/config
$cmd homeassistant/sensor/$1/${1}PowerStatus/config
$cmd homeassistant/sensor/$1/${1}DeviceType/config
$cmd homeassistant/sensor/$1/${1}LastBoot/config
$cmd homeassistant/binary_sensor/$1/config

