from machine import ADC , Pin 
from Blocky.Pin import getPin
class Light :
	def __init__ (self , port , sensitivity = 4):
		pin = getPin(port)
		if (pin[2] == None):
			from machine import reset
			reset()
		
		self.adc = ADC(Pin(pin[2]))
		if (sensitivity == 1): self.adc.atten(ADC.ATTN_0DB)
		elif (sensitivity == 2): self.adc.atten(ADC.ATTN_2_5DB)
		elif (sensitivity == 3): self.adc.atten(ADC.ATTN_6DB)
		elif (sensitivity == 4): self.adc.atten(ADC.ATTN_11DB)
	def read(self):
		return self.adc.read()
		