from machine import Pin 
from Blocky.Timer import AddTask
from Blocky.Pin import getPin

class Buzzer:
	def __init__(self,port):
		self.mode = None
		self.beeptime = 0
		self.beepgap = 0
		self.speed = 0
	def _handler(self):
		self.beeptime -= 1
		if self.beeptime % 2 == 0:
			self.buzzer.value(0)
		else :
			self.buzzer.value(1)
		if self.beeptime == 0:
			return 
		AddTask(mode='once',function=self._handler,period=self.speed)
		
	def beep(self,time=1,speed=200):
		self.beeptime = time*2
		self.speed = speed
		self._handler()
		