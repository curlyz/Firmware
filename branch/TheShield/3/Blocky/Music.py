#from blocky_utility import get_free_UART TODO
from machine import Pin , UART
from Blocky.Pin import getPin
from time import sleep_ms as delay
from time import ticks_diff,ticks_ms
import binascii
class Music :
	def __init__ ( self , port ):
		pin = getPin(port)
		if (pin[0]==None or pin[1] == None):
			from machine import reset 
			reset()
		self.bus = UART(1 , 9600)
		self.bus.init(baudrate = 9600 , bits = 8 , parity = None , stop = 1 , rx = pin[0] , tx = pin[1] )
	
	def sendStack(self , cmd , param1 , param2):
		while self.bus.any():
			self.bus.read()
			
		buff = bytearray([0x7E, 0xFF, 0x06, cmd,0x01, param1, param2, 0xEF])
		self.bus.write(buff)
		nowTime = ticks_ms()
		while not self.bus.any():
			if ticks_diff(ticks_ms() , nowTime) > 5000:
				return 


		
	#=====================================================
	def nextSong(self):
		self.sendStack(0x01,0x00,0x00)
	def previousSong(self):
		self.sendStack(0x02,0x00,0x00)
	def playSong( self , fileNumber ):
		self.sendStack(0x03, fileNumber//256 , fileNumber%256)
	def volumeUp(self):
		self.sendStack(0x04,0x00,0x00)
	def volumeDown(self):
		self.sendStack(0x05,0x00,0x00)
	def volume(self , volume):
		self.sendStack(0x06 , 0x00 , volume)
	def setEqualizer(self , eq):
		self.sendStack(0x07 , 0x00 , eq)
	def playLoop ( self , fileNumber):
		self.sendStack(0x08, fileNumber//256 , fileNumber%256)
	def outputDevice( self , device):
		self.sendStack(0x09,0x00,device)
		delay(200)
	def sleep(self):
		self.sendStack(0x0A, 0x00,0x00)
	def reset(self):
		self.sendStack(0x0C,0x00,0x00)
		delay(2000)
	def start(self):
		self.sendStack(0x0D,0x00,0x00)
	def pause(self):
		self.sendStack(0x0E,0x00,0x00)
	def playFolder(self,folder,song):
		self.sendStack(0x0F,folder,song)
	def outputSetting(self,enable,gain):
		self.sendStack(0x10,enable,gain)
	def enableLoopAll(self):
		self.sendStack(0x11,0x00,0x01)
	def disableLoopAll(self):
		self.sendStack(0x11,0x00,0x00)
	def playMP3Folder(self,file):
		self.sendStack(0x12,file//256,file%256)
	def advertise( self,file):
		self.sendStack(0x13,file//256,file%256)
	def stopAdvertise(self):
		self.sendStack(0x15)
		self.sendStack(0x16,0x00,0x00)
	def stop(self):
		self.sendStack(0x16,0x00,0x00)
	def loopFolder(self,folderNumber):
		self.sendStack(0x17, folderNumber//256,folderNumber%256)
	def randomAll(self):
		self.sendStack(0x18,0x00,0x00)
	def enableLoop(self):
		self.sendStack(0x19, 0x00,0x00)
	def disableLoop(self):
		self.sendStack(0x19, 0x01,0x00)
	def enableDAC(self):
		self.sendStack(0x1A, 0x00,0x00)
	def disableDAC(self):
		self.sendStack(0x1A, 0x01,0x00)
	def readState(self):
		return self._readRegister(0x42)
	def readVolume(self):
		return self._readRegister(0x43)
	def readEQ(self):
		return self._readRegister(0x44)
	def readFileCounts(self):
		return self._readRegister(0x48)
	def readCurrentFileNumber(self):
		return self._readRegister(0x4C)
	def readFileCountsInFolder(self,folder):
		return self._readRegister(0x4E,folder)
	def readFolderCounts(self):
		return self._readRegister(0x4F)
	def _readRegister(self,cmd,param=None):
		nowTime = ticks_ms()
		while self.bus.any() :
			self.bus.read()
			
		if param == None :
			self.sendStack(cmd,0x00,0x00)
		else :
			self.sendStack(cmd,param//256,param%256)
		while not self.bus.any():
			if ticks_diff(ticks_ms() , nowTime) > 1000:
				return None
		buffer = self.bus.read(10)
		print(buffer)
		return buffer[5]*256 + buffer[6]


