#!/usr/bin/python3

import pysimpledmx.pysimpledmx as pysimpledmx
import webcolors, colorsys
import sys, configparser
import simplejson as json
import lib.mymqtt as mymqtt

# 
# Clamp values between a range - inclusive
#
def clamp(n, smallest=0, largest=255): return max(smallest, min(n, largest))

#
# Convert HSV in PERCENT (not DEGREES) to RGB (0..255)
#
def hsv_to_rgb(h, s, v):
   # colorsys only does floats from 0 to 1 for all inputs and outputs
   # smartthings only reports h,s,v as a percent 0 to 100
   # convert smartthings percent to float
   h = float(h)/100.0
   s = float(s)/100.0
   v = float(v)/100.0
   r, g, b = colorsys.hsv_to_rgb(h, s, v)
   # convert to r,g,b web space (0-255)
   r = int(r*255.0)
   g = int(g*255.0)
   b = int(b*255.0)
   return (r, g, b)

#
# ParFixture
# 
# LED PAR DMX Channels:
# 1 - master dimming - 0 (dark) to 255 (light)
# 2 - master strobe - 0 (slow) to 255 (fast)
# 3 - function
#    DMX 8 control    0 - 50
#    Jumping change     51-100
#    Gradual change    101-150
#    Pulse change   151-200
#    Sound control    201-255 (does not work)
# 4 - function speed - 0 (slow) to 255 (fast)
# 5 - Red dimming
# 6 - Green dimming
# 7 - Blue dimming
#
# Each channel mapped to an attribute.
#
class ParFixture:
   mydmx = 0 # controller handle
   channel = 0 # fixture channel

   # all the keys will be initialized as class attributes
   allowed_keys = set(['dimmer','strobe','function', 'speed',
            'red', 'blue', 'green'])

   # map DMX values for fixture function to labels
   fixtureFunction = {0: 0, 'dmx': 0, 'jump': 55, 'gradual': 105,
            'pulse': 155, 'sound': 205 }

   # Set all attributes to 0
   def reset(self):
      self.__dict__.update((key, 0) for key in self.allowed_keys)
      self.effect = ''

   # Fixture Off
   def off(self):
      self.reset()
      self.setChannel()
   
   # Shortcut to set all attributes from a dict
   def setParams(self, **kwargs):
      # and update the given keys by their given values
      self.__dict__.update((key, value) for key, value in kwargs.items() if key in self.allowed_keys)
      self.setChannel()

   # Set color from RGB color space values
   # expects values: red, green, blue, dimmer
   # NOTE: Performs color correction for DMX fixture by adjusting
   #       values by percentages to achieve 'white' output
   def setRGB(self, r, g, b, d=255):
      # reset fixture values to all off
      self.reset()

      # color correction for the fixtures
      # color correct blue only if some green is specified
      gamma = 0.33
      if r or g:
         b = b * gamma
      b = int(clamp(b))

      # color correct green only if some blue is specified
      alpha = 0.55
      if r or b:
         g = g * alpha
      g = int(clamp(g))

      beta = 1
      if b or g:
         r = r * beta
      r = int(clamp(r))

      self.setParams(**{'dimmer': d, 'red': r, 'green': g, 'blue': b})
      # set the channel params, but not rendered
      self.setChannel()

   # Set color from HSV color space values
   # need to consider brightness of dimmer setting?
   def setHSV(self, h, s, v, d=255):
      r, g, b = hsv_to_rgb(h, s, v)
      self.setRGB(r, g, b, d)
   
   # Set DMX Channel values based on object attribute values
   # NOTE: Does not take affect until rendered by DMX controller
   def setChannel(self):
      self.mydmx.setChannel(self.channel+1, self.dimmer)
      self.mydmx.setChannel(self.channel+2, self.strobe)
      self.mydmx.setChannel(self.channel+3, self.fixtureFunction[self.function])
      self.mydmx.setChannel(self.channel+4, self.speed)
      self.mydmx.setChannel(self.channel+5, self.red)
      self.mydmx.setChannel(self.channel+6, self.green)
      self.mydmx.setChannel(self.channel+7, self.blue)

   # Init for Fixture - Everything Off
   # Accepts starting channel for DMX addressing
   def __init__(self, dmxController, channel, **kwargs):
      self.mydmx = dmxController
      self.channel = channel
      # init all params to 0 or off
      self.off()

#
# DMXController
#
class DMXController:
   fixtures = list()
   effect = ''
   state = 'OFF'

   # all the keys will be initialized as class attributes
   allowed_keys = set(['dimmer', 'red', 'blue', 'green'])
   
   # Add a PAR fixture to control set
   def addPar(self, channel):
      par = ParFixture(self, channel)
      self.fixtures.append(par)
      return par

   # Render all changes to DMX bus
   def render(self):
      self.mydmx.render() # render all of the above changes onto the DMX network
      if self.dimmer > 0:
         self.state = 'ON'

   # Set the DMX channel to specified value
   # NOTE: Does not affect fixture until rendered
   def setChannel(self, channel, value):
      self.mydmx.setChannel(channel, value)

   # Set all fixtures to a single color by RGB color space
   def sceneRGB(self, r, g, b, d=255):
      saveParams = {'dimmer': d, 'red': r, 'green': g, 'blue': b}
      self.__dict__.update((key, value) for key, value in iter(saveParams.items()))
      for par in self.fixtures:
         par.setRGB(r, g, b, d)
      self.render()
      self.effect = ''

   # Set all fixtures to a single color by HSV color space percent values
   def sceneHSV(self, h, s, v, d=255):
      r, g, b = hsv_to_rgb(h, s, v)
      self.sceneRGB(r, g, b, d)
   
   # Set all fixtures to a single color by a CSS3 color name string
   def sceneColor(self, color, dimmer=255):
      # convert color to RGB
      try:
         r, g, b = webcolors.name_to_rgb(color)
      except ValueError:
         r, g, b = webcolors.name_to_rgb('white')
      self.sceneRGB(r, g, b, dimmer)

   # Define a Police scene (red, blue, strobe)
   def scenePolice(self):
      for par in self.fixtures:
         par.reset() # reset params
         if self.fixtures.index(par) % 2:
            par.setParams(**{'dimmer': 255, 'strobe': 20, 'red': 255})
         else:
            par.setParams(**{'dimmer': 255, 'strobe': 20, 'blue': 255})
      self.render()

   # Set a scene based on pre-defined labels and associated colors/functions
   def setScene(self, name):
      if name == 'police':
         self.scenePolice()
      elif name == 'movie':
         self.sceneRGB(255, 144, 21, 77)
      elif name == 'colorloop':
         self.allFixtures(**{'dimmer': 255, 'function': 'gradual', 'speed': 125})
      elif name == 'party':
         self.allFixtures(**{'dimmer': 255, 'function': 'jump', 'speed': 200})
      elif name == 'sound':
         self.allFixtures(**{'dimmer': 255, 'function': 'sound', 'speed': 200})
      elif name == 'night':
         self.sceneRGB(36, 91, 255, 130)
      elif name == 'reset':
         self.sceneColor('white', 255)
      # set effect last as it is reset by methods above
      self.effect = name

   # Pass a set of parameters to all fixtures and render the result
   def allFixtures(self, **kwargs):
      for par in self.fixtures:
         par.reset()  # clear old params
         par.setParams(**kwargs)
      self.render()

   # Turn Off all Fixtures
   def off(self):
      for par in self.fixtures:
         par.off()
      self.render()
      self.state = 'OFF'
   
   # Control dimmer of all fixtures
   # NOTE: Side-Affect - sets fixtures to a single color!
   # eg. This would break scene 'police'
   def dimOnly(self, d):
      self.sceneRGB(self.red, self.green, self.blue, d)
   
   # Set Fixtures to last known color and brightness
   # NOTE: Side-Affect - sets fixtures to a single color!
   # eg. This would break scene 'police'
   def on(self):
      self.sceneRGB(self.red, self.green, self.blue, self.dimmer)
      self.state = 'ON'

   def on_message(self, client, message):
      params = json.loads(message.payload.decode('utf-8'))
      status = {}

      if ('brightness' in params):
         self.dimOnly(int(params['brightness']))
      if ('state' in params):
         if params['state'] == 'ON':
            self.on()
         else:
            self.off()
      if ('color' in params):
         r = int(params['color']['r'])
         g = int(params['color']['g'])
         b = int(params['color']['b'])
         self.sceneRGB(r, g, b, self.dimmer)
      if ('effect' in params):
         self.setScene(params['effect'])
      
      status['state'] = self.state
      status['brightness'] = self.dimmer
      status['color'] = {}
      status['color']['r'] = self.red
      status['color']['g'] = self.green
      status['color']['b'] = self.blue
      status['effect'] = self.effect

      # Send the message back
      client.update(status, fmt='json', retain=True)
      return

   # Init controller
   # Starting values for fixture attributes set to 255 (r,g,b,d)
   # Those starting values enable self.on to light up all fixtures.
   def __init__(self):
      self.__dict__.update((key, 0) for key in self.allowed_keys)
      self.mydmx = pysimpledmx.DMXConnection('/dev/ttyUSB0')


def main():
   # load the device config
   config = configparser.ConfigParser()
   config.read('../config/config.ini')

   status = {}
   if len(sys.argv) > 1:
      cmd = sys.argv[1]
      mydmx = pysimpledmx.DMXConnection('/dev/ttyUSB0')

      if cmd == 'off':
         mydmx.setChannel(11, 0)
         mydmx.setChannel(12, 0)
         mydmx.setChannel(13, 0)
         mydmx.setChannel(14, 0)
         mydmx.setChannel(15, 0)
         mydmx.setChannel(16, 0)
         mydmx.setChannel(17, 0)

         mydmx.setChannel(21, 0)
         mydmx.setChannel(22, 0)
         mydmx.setChannel(23, 0)
         mydmx.setChannel(24, 0)
         mydmx.setChannel(25, 0)
         mydmx.setChannel(26, 0)
         mydmx.setChannel(27, 0)

      elif cmd == 'test':
         mydmx.setChannel(11, 255)
         mydmx.setChannel(12, 0)
         mydmx.setChannel(13, 0)
         mydmx.setChannel(14, 0)
         mydmx.setChannel(15, 255)
         mydmx.setChannel(16, 180)
         mydmx.setChannel(17, 90)

         mydmx.setChannel(21, 255)
         mydmx.setChannel(22, 0)
         mydmx.setChannel(23, 0)
         mydmx.setChannel(24, 0)
         mydmx.setChannel(25, 255)
         mydmx.setChannel(26, 180)
         mydmx.setChannel(27, 90)

      mydmx.render() # render all of the above changes onto the DMX network

   else:
      try:
         # initialization
         mydmx = DMXController()
         par1 = mydmx.addPar(10)
         par2 = mydmx.addPar(20)
         mydmx.render()
         # set white as preset so turn 'ON' works as expected
         mydmx.sceneColor('white')
         mydmx.off()

         client = mymqtt.mymqtt(config, mydmx)

         # Wait forever for msgs
         client.loop_forever()

      except:
         mydmx.off()

   return

if __name__ == '__main__':
   main()
