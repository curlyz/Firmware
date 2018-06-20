from Blocky.Timer import AddTask , time ,UpdateTask
from Blocky.Pin import getPin
from machine import Pin
from micropython import const

DEBOUNCE = const(100)

class Button:
	def __init__(self,port):
		pin = getPin(port)
		if pin[0] == None :
			return 
		self.p = pin[0]
		self.last_time = time()
		self.last_state = 0
		self.number = 0
		self.ButtonTaskList = [[],[],[],[]]
		self.ButtonHistory = []
		self.button = Pin(pin[0],Pin.IN,Pin.PULL_DOWN)
		self.button.irq(trigger=Pin.IRQ_RISING|Pin.IRQ_FALLING,handler=self._handler)
	def event(type,time,function):
		if type == 'press':		
			self.ButtonTaskList[0]=(time,function)
		elif type == 'release':	
			self.ButtonTaskList[1]=(time,function)
		elif type == 'push':		
			self.ButtonTaskList[2].append((time,function))
			self.ButtonTaskList[2].sort()
			AddTask(name = 'Button' , function = self.push_handler , mode = 'once' , period = 999999999)
		elif type == 'hold':		
			self.ButtonTaskList[3].append((time*1000,function))
			self.ButtonTaskList[3].sort()
			
	def push_handler(self):
		if self.button.value() == 0:
			pushed = len(ButtonHistory) //2
			for i in range(len(ButtonTaskList[2])):
				if ButtonTaskList[2][i][0]==pushed:
					try :
						ButtonTaskList[2][i][1]()
					except:
						pass
			ButtonHistory.clear()
		else :
			UpdateTask(name='button'+str(self.p),period = 500)
		
	def _handler(self,source):
		state = self.button.value()
		now = time()
		if state != self.last_state:
			self.last_state = state 
			self.ButtonHistory.append((time(),state))
			if self.ButtonTaskList[0]:
				if state == 1:
					try :
						self.ButtonTaskList[0][1]()
					except:
						pass
			if self.ButtonTaskList[1] :
				if state == 0:
					try :
						self.ButtonTaskList[1][1]()
					except:
						pass
			if len(self.ButtonTaskList[3]) :
				if len(self.ButtonHistory) > 1 and self.ButtonHistory[-2][1] == 1:
					timegap = now - self.ButtonHistory[-2][0]
					if timegap > 1000 :
						min = 9999999 ; target = 0
						for i in range(len(self.ButtonTaskList[3])):
							if abs(timegap-self.ButtonTaskList[3][i][0]) < min :
								target = i ; min = abs(timegap-self.ButtonTaskList[3][i][0]) 
						if min < 3000 : # min is tolerance
							try :
								self.ButtonTaskList[3][target][1]()
								self.ButtonHistory.clear()
							except:
								pass
			DeleteTask('button' + str(self.p))
			AddTask(name = 'button'+str(self.p) , period = 1000 , mode = 'once' , function = self.push_handler)