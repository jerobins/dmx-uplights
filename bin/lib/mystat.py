"""
System Status library for ease of deploying HA agents.
"""

import psutil, pathlib, threading, time
from datetime import timedelta, timezone, datetime
import simplejson as json

class Job(threading.Thread):
   """
   Job thread class.

   Runs a thread continuously, until forced to stop.
   Executes the provided callback at the specified interval.
   """
   def stop(self):
      """ Told to shutdown; do it. """
      self.stopped.set()
      self.join()
      return

   def run(self):
      """ Execute the task on the interval given. """
      while not self.stopped.wait(self.interval.total_seconds()):
         self.execute(*self.args, **self.kwargs)
      return

   def __init__(self, interval, execute, *args, **kwargs):
      """ Starting the threading party. """
      threading.Thread.__init__(self)
      self.daemon = False
      self.stopped = threading.Event()
      self.interval = interval
      self.execute = execute
      self.args = args
      self.kwargs = kwargs
      return

class mystat:
   """
   MyStat provides an object that will provide system stat reporting via MQTT.
   """
   def stop(self):
      """ Looks like the party is over. """
      self.job.stop()
      return

   def updateSensors(self):
      """ Read all sensors and publish results. """
      topic = "homeassistant/sensor/" + self.deviceName + "/state"
      payload = {}
      
      try:
         payload['temperature'] = self.get_temp()
      except:
         payload['temperature'] = -1

      try:
         payload['disk_use'] = self.get_disk_usage()
      except:
         payload['disk_use'] = -1

      try:
         payload['memory_use'] = self.get_memory_usage()
      except:
         payload['memory_use'] = -1

      try:
         payload['cpu_usage'] = self.get_cpu_usage()
      except:
         payload['cpu_usage'] = -1
      
      try:
         payload['power_status'] = self.get_rpi_power_status()
      except:
         payload['power_status'] = -1
      
      try:
         payload['last_boot'] = self.get_last_boot()
      except:
         payload['last_boot'] = -1
      
      try:
         payload['device_type'] = self.get_device_type()
      except:
         payload['device_type'] = -1

      self.client.publish(topic, payload, qos=1, fmt='json')
      return

   def get_last_boot(self):
      """ Last Boot time. """
      tstamp = psutil.boot_time()
      dtstamp = datetime.fromtimestamp(tstamp, timezone.utc)
      localstamp = str(dtstamp.astimezone(tz=None))
      return localstamp

   def get_temp(self):
      """ Get system temperature. """
      result = open(self.SYSTEMP, 'r').read()[:-1]
      if self.is_rpi:
         result = float(result)/1000
         result = str(result)[:4]
      return result

   def get_disk_usage(self):
      """ Disk usage for primary partition. """
      return str(psutil.disk_usage('/').percent)

   def get_memory_usage(self):
      """ Memory usage. """
      return str(psutil.virtual_memory().percent)

   def get_cpu_usage(self):
      """ CPU Usage. """
      return str(psutil.cpu_percent(interval=None))

   def get_rpi_power_status(self):
      """ RPIs will tell us if they are underpowered. """
      if self.is_rpi:
         status = open(self.PWRSTAT, 'r').read()[:-1]
         status = status[:4]
         if status == '0':
            result ='OK'
         else:
            result ='ERROR'
      else:
         result = "Non-Pi"
      return result

   def get_device_type(self):
      """ RPIs will tell us what they are. Pine64 is more cryptic. """
      result = open(self.DEVTYPE, 'r').read()
      return result

   def __init__(self, client):
      """ This is long.
      Define all the sensors for HASSIO MQTT discovery and publish them.
      Publish an initial update for the sensor values.
      Start the thread on a timer to update every 5 minutes.
      """
      self.client = client
      self.deviceName = client.client_id
      self.updateInterval = 300 # 5 mins
      self.is_rpi = pathlib.Path('/etc/rpi-issue').exists()

      self.PWRSTAT = '/sys/devices/platform/soc/soc:firmware/get_throttled'
      self.SYSTEMP = '/sys/class/thermal/thermal_zone0/temp'
      self.DEVTYPE = '/proc/device-tree/model' # works on RPi and Pine64

      # MQTT params
      qos = 1
      retain = True

      status_config_topic = "homeassistant/binary_sensor/" + self.deviceName + "/config"
      status_config = {}
      status_config['name'] = self.deviceName + " Status"
      status_config['state_topic'] = "ha/sbc/" + self.deviceName + "/LWT"
      status_config['availability_topic'] = status_config['state_topic']
      status_config['device_class'] = "connectivity"
      status_config['payload_on'] = "Online"
      status_config['payload_off'] = "Offline"
      status_config['payload_available'] = "Online"
      status_config['payload_not_available'] = "Offline"

      self.client.publish(topic=status_config_topic, payload=status_config, 
                          fmt='json', qos=qos, retain=retain)

      topicPrefix = "homeassistant/sensor/" + self.deviceName
      stateTopic = topicPrefix + "/state"

      temp_config_topic = topicPrefix + "/" + self.deviceName + "Temp/config"
      temp_config = {}
      temp_config['name'] = self.deviceName + " Temperature"
      temp_config['state_topic'] = stateTopic
      temp_config['unit_of_measurement'] = "°C"
      temp_config['value_template'] = "{{ value_json.temperature }}"

      self.client.publish(topic=temp_config_topic, payload=temp_config, 
                          fmt='json', qos=qos, retain=retain)

      disk_config_topic = topicPrefix + "/" + self.deviceName + "DiskUse/config"
      disk_config = {}
      disk_config['name'] = self.deviceName + " Disk Use"
      disk_config['state_topic'] = stateTopic
      disk_config['unit_of_measurement'] = "%"
      disk_config['value_template'] = "{{ value_json.disk_use }}"

      self.client.publish(topic=disk_config_topic, payload=disk_config, 
                          fmt='json', qos=qos, retain=retain)

      mem_config_topic = topicPrefix + "/" + self.deviceName + "MemoryUse/config"
      mem_config = {}
      mem_config['name'] = self.deviceName + " Memory Use"
      mem_config['state_topic'] = stateTopic
      mem_config['unit_of_measurement'] = "%"
      mem_config['value_template'] = "{{ value_json.memory_use }}"

      self.client.publish(topic=mem_config_topic, payload=mem_config, 
                          fmt='json', qos=qos, retain=retain)

      cpu_config_topic = topicPrefix + "/" + self.deviceName + "CpuUsage/config"
      cpu_config = {}
      cpu_config['name'] = self.deviceName + " CPU Usage"
      cpu_config['state_topic'] = stateTopic
      cpu_config['unit_of_measurement'] = "%"
      cpu_config['value_template'] = "{{ value_json.cpu_usage }}"

      self.client.publish(topic=cpu_config_topic, payload=cpu_config, 
                          fmt='json', qos=qos, retain=retain)

      power_config_topic = topicPrefix + "/" + self.deviceName + "PowerStatus/config"
      power_config = {}
      power_config['name'] = self.deviceName + " Power Status"
      power_config['state_topic'] = stateTopic
      power_config['value_template'] = "{{ value_json.power_status }}"

      self.client.publish(topic=power_config_topic, payload=power_config, 
                          fmt='json', qos=qos, retain=retain)

      devtype_config_topic = topicPrefix + "/" + self.deviceName + "DeviceType/config"
      devtype_config = {}
      devtype_config['name'] = self.deviceName + " Device Type"
      devtype_config['state_topic'] = stateTopic
      devtype_config['value_template'] = "{{ value_json.device_type }}"

      self.client.publish(topic=devtype_config_topic, payload=devtype_config, 
                          fmt='json', qos=qos, retain=retain)

      boot_config_topic = topicPrefix + "/" + self.deviceName + "LastBoot/config"
      boot_config = {}
      boot_config['name'] = self.deviceName + " Last Boot"
      boot_config['state_topic'] = stateTopic
      boot_config['value_template'] = "{{ value_json.last_boot }}"

      self.client.publish(topic=boot_config_topic, payload=boot_config, 
                          fmt='json', qos=qos, retain=retain)

      # send an update on start-up
      self.updateSensors()

      self.job = Job(interval=timedelta(seconds=self.updateInterval), 
                     execute=self.updateSensors)
      self.job.start()

      return
