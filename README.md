# DMX-Uplights

See config/ directory for the particulars.

* config/config.ini
* config/setup.sh

bin/dmx-mqtt.py has the hard-coded fixture setup as I only have two fixtures and they are identical.

This repo is for sharing some code and is not supported in any way.

Sample HA light config:

    platform: mqtt
    schema: json
    name: Uplights
    command_topic: ha/light/rgb/uplights/set
    state_topic: ha/light/rgb/uplights
    availability_topic: ha/sbc/uplights/LWT
    payload_available: 'Online'
    payload_not_available: 'Offline'
    brightness: true
    effect: true
    effect_list:
      - police
      - movie
      - party
      - colorloop
      - sound
      - night
      - reset
    rgb: true
    retain: true
