import serial, sys, array

START_VAL   = 0x7E
END_VAL     = 0xE7

COM_BAUD    = 57600
COM_TIMEOUT = 1
COM_PORT    = 7
DMX_SIZE    = 512

LABELS = {
         'GET_WIDGET_PARAMETERS' :0x03,  #unused
         'SET_WIDGET_PARAMETERS' :0x04,  #unused
         'RX_DMX_PACKET'         :0x05,  #unused
         'TX_DMX_PACKET'         :0x06,
         'TX_RDM_PACKET_REQUEST' :0x07,  #unused
         'RX_DMX_ON_CHANGE'      :0x08,  #unused
      }


class DMXConnection(object):
  def __init__(self, comport = None):
    '''
    On Windows, the only argument is the port number. On *nix, it's the path to the serial device.
    For example:
        DMXConnection(4)              # Windows
        DMXConnection('/dev/tty2')    # Linux
        DMXConnection("/dev/ttyUSB0") # Linux
    '''
    self.dmx_frame = [0] * DMX_SIZE
    try:
      self.com = serial.Serial(comport, baudrate = COM_BAUD, timeout = COM_TIMEOUT)
    except:
      com_name = 'COM%s' % (comport + 1) if type(comport) == int else comport
      print("Could not open device %s. Quitting application." % com_name)
      sys.exit(0)

    # print "Opened %s." % (self.com.portstr)


  def setChannel(self, chan, val, autorender = False):
    '''
    Takes channel and value arguments to set a channel level in the local
    DMX frame, to be rendered the next time the render() method is called.
    '''
    if not 1 <= chan <= DMX_SIZE:
      print('Invalid channel specified: %s' % chan)
      return
    # clamp value
    val = max(0, min(val, 255))
    self.dmx_frame[chan-1] = val
    if autorender: self.render()

  def clear(self, chan = 0):
    '''
    Clears all channels to zero. blackout.
    With optional channel argument, clears only one channel.
    '''
    if chan == 0:
      self.dmx_frame = [0] * DMX_SIZE
    else:
      self.dmx_frame[chan-1] = 0


  def render(self):
    ''''
    Updates the DMX output from the USB DMX Pro with the values from self.dmx_frame.
    '''
    packet = array.array('B')
    packet.append(START_VAL)
    packet.append(LABELS['TX_DMX_PACKET'])
    packet.append(len(self.dmx_frame) & 0xFF)
    packet.append((len(self.dmx_frame) >> 8) & 0xFF)
    packet.fromlist(self.dmx_frame)
    packet.append(END_VAL)

    self.com.write(packet.tobytes())

  def close(self):
    self.com.close()
