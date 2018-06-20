from machine import ADC , Pin 
from Blocky.Pin import getPin
class Smoke :
	def __init__ (self , port , sensitivity = 4):
		if (getPin(port)[2] == None):
			from machine import reset
			reset()
		self.adc = ADC(getPin[2])
		if (sensitivity == 1) self.adc.atten(ADC.ATTN0_DB)
		elif (sensitivity == 2) self.adc.atten(ADC.ATTN_2_5DB)
		elif (sensitivity == 3) self.adc.atten(ADC.ATTN6_DB)
		elif (sensitivity == 4) self.adc.atten(ADC.ATTN11_DB)
	def read(self):
		return self.adc.read()
		