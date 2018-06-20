from machine import Pin
from neopixel import NeoPixel
from Blocky.Pin import getPin
class RGB:
  def __init__(self,port , num):
    p = getPin(port)
    if p[0] == None :
      return 
    self.rgb = NeoPixel(Pin(p[0]) , num , timing = True)
  def setColor(self , list , color):
    for i in range(0,len(list)):
      self.rgb[list[i]] = color
    self.rgb.write()
    
