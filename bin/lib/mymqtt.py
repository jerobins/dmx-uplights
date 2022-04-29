"""
  My MQTT library for ease of deploying HA agents.

  The following entries are expected in the config dictionary:

  [main]
  mqttServer
  mqttPort
  mqttUser
  mqttPass
  mqttSet
  mqttState
  mqttId
"""

# TODO: augment LWT with interrupt handler to call specified function

import socket, time
import simplejson as json
import paho.mqtt.publish as mqtt
import paho.mqtt.client as mqttclient
import lib.mystat as mystat

class mymqtt:
   """
   MyMQTT provides an MQTT object that will provide a persistent connection 
   and handle dispatching callbacks on received messages.

   It also supports multiple subscriptions.
   """

   def do_connect(self):
      """
      Try to connect...and keep trying in the event of a disconnect.
      """
      while True:
         try:
            self.mqttc.connect(self.mqtt_serv, self.mqtt_port)
            break
         except:
            time.sleep(15)
      return

   def on_connect(self, client, userdata, flags, rc):
      """
      When we do connect, subscribe to the primary topic.
      Also, publish the LWT to let folks know we alive.
      """
      client.subscribe(self.set_topic)
      self.publish(topic=self.lwt_topic, payload='Online', retain=True)
      return

   def on_message(self, client, userdata, message):
      """
      Hello? Pass the message to the recipient.
      """
      userdata.on_message(self, message)
      return

   def add_sub(self, topic):
      """ Fancy clients may need to listen to secondary topics. """
      self.mqttc.subscribe(topic)
      return

   def publish(self, topic='None', payload='None', fmt='plain', retain=False, qos=1):
      """ Take a payload and publishes to defined MQTT topic.
      Format can be 'plain' or 'json'. If json, payload should be a dict.
      """
      if fmt == 'plain':
         # must go out as string
         payload = str(payload)
      else:
         payload = json.dumps(payload)

      # don't fail if we try to publish but are not connected
      try:
         self.mqttc.publish(topic=topic, payload=payload, 
                            qos=qos, retain=retain)
      except:
         pass

      return

   def update(self, payload='None', fmt='plain', qos=1, retain=False):
      """ Publish an update to the primary topic. """
      self.publish(topic=self.state_topic, payload=payload, 
                   fmt=fmt, qos=qos, retain=retain)
      return

   def loop_forever(self):
      """ You have seen Primer(2004), correct?
      If the loop does stop, kill the stats thread.
      """ 
      try:
         self.mqttc.loop_forever()
      except:
         self.stats.stop()
      return

   def loop_start(self):
      """ t=0 """
      self.mqttc.loop_start()
      return

   def loop_stop(self):
      """ Uh-oh. If it is the end, let's make sure we are all dead. """
      self.mqttc.loop_stop()
      self.stats.stop()
      return

   def __init__(self, config, userdata=None):
      """ This is how we start an IOT party.
       - find our client_id
       - generate our topic strings based on the id
       - set instance variables
       - pass userdata object handlers
       - configure LWT
       - kick off MQTT start-up
       - start a stats thread to post MQTT stats messages about this device
      """
      self.client_id = socket.gethostname()

      self.mqttc = mqttclient.Client(self.client_id)
      self.mqttc.disable_logger()

      self.set_topic = config['main']['mqttSet'].replace('CID', self.client_id)
      self.state_topic = config['main']['mqttState'].replace('CID', self.client_id)
      self.lwt_topic = "ha/sbc/" + self.client_id + "/LWT"

      self.mqtt_user = config['main']['mqttUser']
      self.mqtt_pass = config['main']['mqttPass']
      self.mqtt_serv = config['main']['mqttServer']
      self.mqtt_port = int(config['main']['mqttPort'])

      self.mqttc.username_pw_set(self.mqtt_user, self.mqtt_pass)

      # pass the userdata object to handlers
      self.mqttc.user_data_set(userdata)

      # set will to be executed if we disconnect prematurely
      self.mqttc.will_set(self.lwt_topic, 'Offline', retain=True)

      self.mqttc.on_connect = self.on_connect
      self.mqttc.on_message = self.on_message

      self.do_connect()

      if (config['main'].getboolean('stats', fallback=True)):
        self.stats = mystat.mystat(self)

      return
