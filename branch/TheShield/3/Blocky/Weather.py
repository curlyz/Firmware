from machine import Pin
from dht import *
from Blocky.Pin import getPin

class Weather:
	def __init__ (self , port,type='DHT11'):
		pin = getPin(port)
		if (pin[0] == None):
			from machine import reset
			reset()
		if type == 'DHT11': self.weather = DHT11(Pin(pin[0]))
		elif type == 'DHT22': self.weather = DHT22(Pin(pin[0]))
		elif type == 'DHTBase': self.weather = DHTBase(Pin(pin[0]))
		else :
			raise NameError
	  
	def temperature (self):
		self.weather.measure()
		return self.weather.temperature()
	def humidity(self):
		self.weather.measure()
		return self.weather.humidity()
   
