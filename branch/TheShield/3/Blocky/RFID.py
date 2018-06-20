# Example of detecting and reading a block from a MiFare NFC card.
# Author: Manuel Fernando Galindo (mfg90@live.com)
#
# Copyright (c) 2016 Manuel Fernando Galindo
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from Blocky.Timer import AddTask
from Blocky.Pin import *

import binascii
import array
#from functools import reduce
from time import *
#import serial

PN532_PREAMBLE						= 0x00
PN532_STARTCODE1					= 0x00
PN532_STARTCODE2					= 0xFF
PN532_POSTAMBLE						= 0x00

PN532_HOSTTOPN532					= 0xD4
PN532_PN532TOHOST					= 0xD5

# PN532 Commands
PN532_COMMAND_DIAGNOSE				= 0x00
PN532_COMMAND_GETFIRMWAREVERSION	= 0x02
PN532_COMMAND_GETGENERALSTATUS		= 0x04
PN532_COMMAND_READREGISTER			= 0x06
PN532_COMMAND_WRITEREGISTER			= 0x08
PN532_COMMAND_READGPIO				= 0x0C
PN532_COMMAND_WRITEGPIO				= 0x0E
PN532_COMMAND_SETSERIALBAUDRATE		= 0x10
PN532_COMMAND_SETPARAMETERS			= 0x12
PN532_COMMAND_SAMCONFIGURATION		= 0x14
PN532_COMMAND_POWERDOWN				= 0x16
PN532_COMMAND_RFCONFIGURATION		= 0x32
PN532_COMMAND_RFREGULATIONTEST		= 0x58
PN532_COMMAND_INJUMPFORDEP			= 0x56
PN532_COMMAND_INJUMPFORPSL			= 0x46
PN532_COMMAND_INLISTPASSIVETARGET	= 0x4A
PN532_COMMAND_INATR					= 0x50
PN532_COMMAND_INPSL					= 0x4E
PN532_COMMAND_INDATAEXCHANGE		= 0x40
PN532_COMMAND_INCOMMUNICATETHRU		= 0x42
PN532_COMMAND_INDESELECT			= 0x44
PN532_COMMAND_INRELEASE				= 0x52
PN532_COMMAND_INSELECT				= 0x54
PN532_COMMAND_INAUTOPOLL			= 0x60
PN532_COMMAND_TGINITASTARGET		= 0x8C
PN532_COMMAND_TGSETGENERALBYTES		= 0x92
PN532_COMMAND_TGGETDATA				= 0x86
PN532_COMMAND_TGSETDATA				= 0x8E
PN532_COMMAND_TGSETMETADATA			= 0x94
PN532_COMMAND_TGGETINITIATORCOMMAND = 0x88
PN532_COMMAND_TGRESPONSETOINITIATOR = 0x90
PN532_COMMAND_TGGETTARGETSTATUS		= 0x8A

PN532_RESPONSE_INDATAEXCHANGE		= 0x41
PN532_RESPONSE_INLISTPASSIVETARGET	= 0x4B

PN532_WAKEUP						= 0x55

PN532_SPI_STATREAD					= 0x02
PN532_SPI_DATAWRITE					= 0x01
PN532_SPI_DATAREAD					= 0x03
PN532_SPI_READY						= 0x01

PN532_MIFARE_ISO14443A				= 0x00

# Mifare Commands
MIFARE_CMD_AUTH_A					= 0x60
MIFARE_CMD_AUTH_B					= 0x61
MIFARE_CMD_READ						= 0x30
MIFARE_CMD_WRITE					= 0xA0
MIFARE_CMD_TRANSFER					= 0xB0
MIFARE_CMD_DECREMENT				= 0xC0
MIFARE_CMD_INCREMENT				= 0xC1
MIFARE_CMD_STORE					= 0xC2
MIFARE_ULTRALIGHT_CMD_WRITE			= 0xA2


#PN532_ACK_STRING					= "0000ff00ff00"
PN532_ACK_STRING					= bytearray([0x00,0x00,0xFF,0x00,0xFF,0x00])
#PN532_ACK_FRAME						= "\x00\x00\xFF\x00\xFF\x00"
PN532_ACK_FRAME						= bytearray([0x00,0x00,0xFF,0x00,0xFF,0x00])


def millis():
	return ticks_ms()
def reduce(function, iterable, initializer=None):
    it = iter(iterable)
    if initializer is None:
        try:
            initializer = next(it)
        except StopIteration:
            raise TypeError('reduce() of empty sequence with no initial value')
    accum_value = initializer
    for x in it:
        accum_value = function(accum_value, x)
    return accum_value
class RFID(object):

	def __init__(self, port , uart_baudrate = 115200):
		self.last = None
		self.status = False
		self.message = ""
		pin = getPin(port)
		self.pin = pin[0]
		
		self.cb = None
		try:
			from machine import UART 
			self.ser = UART ( 1 , tx = pin[0] , rx = pin[1] , baudrate = 115200 )
			self.status = True
			self.begin()
			self.SAM_configuration()
			AddTask(name='rfid'+str(self.pin) , mode = 'repeat' , period = 500 , function = self._handler)
		except Exception:
			self.status = False

	def _uint8_add(self, a, b):
		"""Add add two values as unsigned 8-bit values."""
		return ((a & 0xFF) + (b & 0xFF)) & 0xFF

	def _busy_wait_ms(self, ms):
		"""Busy wait for the specified number of milliseconds."""
		start = ticks_ms()
		delta = ms
		while (ticks_ms() - start) <= delta:
			pass

	def _write_frame(self, data):
		ack = False
		"""Write a frame to the PN532 with the specified data bytearray."""
		assert data is not None and 0 < len(data) < 255, 'Data must be array of 1 to 255 bytes.'
		# Build frame to send as:
		# - Preamble (0x00)
		# - Start code	(0x00, 0xFF)
		# - Command length (1 byte)
		# - Command length checksum
		# - Command bytes
		# - Checksum
		# - Postamble (0x00)
		length = len(data)
		frame = bytearray(length+7)
		frame[0] = PN532_PREAMBLE
		frame[1] = PN532_STARTCODE1
		frame[2] = PN532_STARTCODE2
		frame[3] = length & 0xFF
		frame[4] = self._uint8_add(~length, 1)
		frame[5:-2] = data
		checksum = reduce(self._uint8_add, data, 0xFF)
		frame[-2] = ~checksum & 0xFF
		frame[-1] = PN532_POSTAMBLE
		# Send frame.
		#self.ser.flushInput()
		while(not ack):
			self.ser.write(frame)
			ack = self._ack_wait(1000)
			sleep_ms(300)
		return ack


	def _ack_wait(self, timeout):
		ack=False
		rx_info=bytearray()
		start_time = millis()
		current_time = start_time
		while((current_time - start_time) < timeout and not ack):
			sleep_ms(120)#Stability on receive
			while self.ser.any():
				#rx_info += str(hex(self.ser.read()))
				rx_info.extend(self.ser.read());#%print(len(rx_info))#;#%print('RECEOVE',rx_info)#self.ser.inWaiting()

			current_time = millis()
			##%print(str(rx_info.encode("hex")))
			if True :#(PN532_ACK_STRING in str(rx_info.encode("hex"))):
				ack = True
				#%print('ACKKKKKKKKKKKKK')
			#%print('StringReceived' , rx_info , len(rx_info))
		if(ack):
			if(len(rx_info)>6):
				#rx_info=rx_info.split(PN532_ACK_FRAME)
				self.message = rx_info
			else:
				self.message = rx_info
				#%print('NOWMESS' , self.message, type(self.message))
			#self.ser.flush()
			return ack
		else:
			self.message = ""
			return ack

	def _read_data(self, count):
		timeout = 1000
		rx_info=""
		if(self.message == ""):
			self._ack_wait(1000)
		else:
			rx_info = self.message
			#%print('MESS',self.message)
		##%print(type(rx_info) , rx_info)
		
		return rx_info

	def _read_frame(self, length):
		"""Read a response frame from the PN532 of at most length bytes in size.
		Returns the data inside the frame if found, otherwise raises an exception
		if there is an error parsing the frame.	 Note that less than length bytes
		might be returned!
		"""
		# Read frame with expected length of data.
		response = self._read_data(length+8) # a string "\x00\x00\xFF\x00\xFF\x00" 
		#response = ''.join(response)
		#%print("READFRAME", end = '\t')
		#for i in range(len(response)):#%print(response[i],end='\t')
		#%print()
		# Check frame starts with 0x01 and then has 0x00FF (preceeded by optional
		# zeros).
		frame_len = 0
		offset = 0
		if not len(response):return 'no_card'
		if response[0] != 0:return 'no_card'
		if  (PN532_ACK_FRAME == response):
			#%print('ack_error')
			return 'no_card'
			
		for i in range ( 0 , len(response )):
			if response[i] != 0 and response[i] != 255 :
				frame_len = response[i] 
				offset = i
				break
		
		if frame_len == 0 :
			#%print('LEN_error')
			return 'no_card'
			
			
		if (frame_len + response[offset+1]) & 0xFF != 0:
			#%print('CHECKSUM_error')
			return('no_card')
			# Check frame checksum value matches bytes.
			
		checksum = reduce(self._uint8_add, response[offset+2:offset+2+frame_len+1], 0)
		if checksum != 0:
			#%print('CHECKSUM_errorpART2')
			return('no_card')
		#%print('PACKAGE' , response[offset+2:offset+2+frame_len] )
		return response[offset+2:offset+2+frame_len]

	def wakeup(self):
		msg = '\x55\x55\x00\x00\x00'
		self.ser.write(msg)

	def call_function(self, command, response_length=0, params=[], timeout_sec=1):
		"""Send specified command to the PN532 and expect up to response_length
		bytes back in a response.  Note that less than the expected bytes might
		be returned!  Params can optionally specify an array of bytes to send as
		parameters to the function call.  Will wait up to timeout_secs seconds
		for a response and return a bytearray of response bytes, or None if no
		response is available within the timeout.
		"""
		# Build frame data with command and parameters.
		data = bytearray(2+len(params))
		data[0]	 = PN532_HOSTTOPN532
		data[1]	 = command & 0xFF
		#data[2:(2+len(params)] = params
		for i in range (len(params)):data[2+i]=params[i]
		# Send frame and wait for response.
		if not self._write_frame(data):
			return None
		# Read response bytes.
		#%print('Written')
		response = self._read_frame(response_length+2)
		# Check that response is for the called function.
		if not (response == "no_card"):
			##%print('CORE' , response )
			if not (response[0] == PN532_PN532TOHOST and response[1] == (command+1)):
				raise RuntimeError('Received unexpected command response!')
			# Return response data.
			return response[2:]
		else:
			return response

	def begin(self):
		"""Initialize communication with the PN532.	 Must be called before any
		other calls are made against the PN532.
		"""
		self.wakeup()

	def get_firmware_version(self):
		"""Call PN532 GetFirmwareVersion function and return a tuple with the IC,
		Ver, Rev, and Support values.
		"""
		response = self.call_function(PN532_COMMAND_GETFIRMWAREVERSION, 4)
		if response is None:
			raise RuntimeError('Failed to detect the PN532!	 Make sure there is sufficient power (use a 1 amp or greater power supply), the PN532 is wired correctly to the device, and the solder joints on the PN532 headers are solidly connected.')
		return (response[0], response[1], response[2], response[3])

	def SAM_configuration(self):
		"""Configure the PN532 to read MiFare cards."""
		# Send SAM configuration command with configuration for:
		# - 0x01, normal mode
		# - 0x14, timeout 50ms * 20 = 1 second
		# - 0x01, use IRQ pin
		# Note that no other verification is necessary as call_function will
		# check the command was executed as expected.
		self.call_function(PN532_COMMAND_SAMCONFIGURATION, params=[0x01, 0x14, 0x01])

	def read_passive_target(self, card_baud=PN532_MIFARE_ISO14443A, timeout_sec=1):
		"""Wait for a MiFare card to be available and return its UID when found.
		Will wait up to timeout_sec seconds and return None if no card is found,
		otherwise a bytearray with the UID of the found card is returned.
		"""
		# Send passive read command for 1 card.	 Expect at most a 7 byte UUID.
		response = self.call_function(PN532_COMMAND_INLISTPASSIVETARGET,
									  params=[0x01, card_baud],
									  response_length=17)
                 
		# If no response is available return None to indicate no card is present.
		if response is None:
			return None
		if not (response == "no_card"):
			# Check only 1 card with up to a 7 byte UID is present.
			if response[0] != 0x01:
				raise RuntimeError('More than one card detected!')
			if response[5] > 7:
				raise RuntimeError('Found card with unexpectedly long UID!')
			# Return UID of card.
			list = []
			for x in range( 6 , 6 + response[5]):
				list.append(response[x])
			return list
		else:
			return response
	def event(self,cb):
		self.cb = cb
	def _handler(self):
		now = self.read_passive_target()
		if (self.last != now and now != 'no_card'):
			try :
				self.cb(now);
			except Exception:
				pass
		self.last = now 
	



def a (b):
	print(b)
	
p = RFID(port='D1')
p.event(a)
