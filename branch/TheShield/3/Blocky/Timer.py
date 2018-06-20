from machine import Timer 
from time import ticks_ms

TaskList = []
ScheduleList = []
if '_TimerInfo' not in globals():
  _TimerInfo = [ticks_ms() ,0 ,None,0,False]
#TimerInfo contains the last timer sync, the masterclock
# And the NTP clock to be sync , next interrupt time, task execute
# Timer OVF at 1073741823
def feed():
	return 
def time() : # Return the current runtime 
	global _TimerInfo
	now = ticks_ms()
	
	if now < _TimerInfo[0] :
		offset =  (1073741823 - _TimerInfo[1] + now)
	else :	
		offset =  (now - _TimerInfo[0])
		
	_TimerInfo[1] += offset
	_TimerInfo[0] = now
	
	return _TimerInfo[1]

def clock():
	global _TimerInfo
	if _TimerInfo[2] == None :
		return None 
	else : # TimerInfo[2] = ( _NTP at last sync , _Runtime at last sync )
		return _TimerInfo[2][1] + (time()-_TimerInfo[2][0])//1000
		
	
"""
	Time return the current runtime , does it respond to 
	feed the masterclock ?
	Time use [ticks() , runtime] at that time , compare to the 
	current ticks to come up with the real runtime 
	This method will fail if the timer has been ovf
	Therefore , this funciton must always be run after every 5 minutes
	Handy , it is on _Handler
"""	

if '_Tasker' not in globals():
	_Tasker = Timer(-1)
	
def _TaskHandler(source):
	global TaskList,_TimerInfo
	if _TimerInfo[4] :
		try :
			TaskList[0][2]()
			if TaskList[0][1] == 'repeat':
				TaskList[0][0] += TaskList[0][4]
			elif TaskList[0][1] == 'once':
				TaskList.pop(0)
		except Exception as error :
			print('TaskRemoved >> ',error)
			TaskList.pop(0)
      
		
		finally :
			TaskList.sort()
			
			_TimerInfo[4] = False
	
	# Feed the clock 
	now = time()
	global _Tasker
	
	if len(TaskList) == 0 :
		_TimerInfo[3] = _TimerInfo[1] + 300000 # Call itself every 5 minutes
		_TimerInfo[4] = False
	else :
		if TaskList[0][0]- _TimerInfo[1] < 0 :
			_TimerInfo[3] = _TimerInfo[1] + 1
			_TimerInfo[4] = True
		else :
			if TaskList[0][0] - _TimerInfo[1] > 300000:
				_TimerInfo[3] = _TimerInfo[1] + 300000
				_TimerInfo[4] = False
			else :
				_TimerInfo[3] = _TimerInfo[1] + (TaskList[0][0]-_TimerInfo[1])
				_TimerInfo[4] = True
	
	_Tasker.init(period = (_TimerInfo[3]-_TimerInfo[1]) , mode = Timer.ONE_SHOT , callback = _TaskHandler)
def DeleteTask(name):
	global TaskList , _TimerInfo
	for i in range(len(TaskList)):
		if TaskList[i][3] == name :
			TaskList.pop(i);_TimerInfo[4] = False
			_TaskHandler(False)
			return
def AddTask(function,mode,name=None,**kwargs):
	global TaskList,_TimerInfo
	now = time()
	if not callable(function):
		print('Function not callable')
		return 
	# Task exist ? Then update instead 

	if mode == 'repeat':
		if 'period' in kwargs:
			if type(kwargs['period']) is int :
				TaskList.append([now,mode,function,name,kwargs['period']])

	elif mode == 'once':
		if 'period' in kwargs:
			if type(kwargs['period']) is int :
				TaskList.append([now+kwargs['period'],mode,function,name,kwargs['period']])
	
	elif mode == 'schedule':
		if 'date' in kwargs and 'time' in kwargs:
			global ScheduleList
			ScheduleList.append({'function':function,'name':name,'date':kwargs['date'],'time':kwargs['time']})
			sync_clock()
			
	TaskList.sort()
	
	global _Tasker
	
	if len(TaskList) == 0 :
		_TimerInfo[3] = _TimerInfo[1] + 300000 # Call itself every 5 minutes
		_TimerInfo[4] = False
	else :
		if TaskList[0][0] - _TimerInfo[1] < 0 :
			_TimerInfo[3] = _TimerInfo[1] + 1
			_TimerInfo[4] = True
		else :
			if TaskList[0][0] - _TimerInfo[1] > 300000:
				_TimerInfo[3] = _TimerInfo[1] + 300000
				_TimerInfo[4] = False
			else :
				_TimerInfo[3] = _TimerInfo[1] + (TaskList[0][0]-_TimerInfo[1])
				_TimerInfo[4] = True

	_Tasker.init(period = (_TimerInfo[3]-_TimerInfo[1]) , mode = Timer.ONE_SHOT , callback = _TaskHandler)
		
def UpdateTask ( name , **kwargs ):
	global TaskList
	for i in range(len(TaskList)):
		if TaskList[i][3] == name :
			temp = TaskList[i]
			if 'mode' in kwargs:temp[1] = kwargs['mode']
			if 'period' in kwargs:temp[4] = kwargs['period']
			if 'function' in kwargs:temp[2] = kwargs['function']
			TaskList.pop(i)
			AddTask( function = temp[2] , mode = temp[1],name = name ,period = temp[4] )
			return 
			
def sync_clock(Force = False):
	global _TimerInfo , ScheduleList
	if _TimerInfo[2] == None or Force == True : # Only sync NTP once to avoid float mis-align
		import ustruct , usocket 
		try :
			f = open('System/config.json')
			gmt = ustruct.loads(f.read())['timezone']
		except :
			gmt = 7 # Default for Vietnam timezone
			
		try :
			NTP_QUERY = bytearray(48)
			NTP_QUERY[0] = 0x1b
			s = usocket.socket(usocket.AF_INET,usocket.SOCK_DGRAM)
			s.settimeout(2)
			res = s.sendto(NTP_QUERY,usocket.getaddrinfo("pool.ntp.org",123)[0][-1])
			msg = s.recv(48)
			s.close()
			ntp = ustruct.unpack("!I",msg[40:44])[0]
			ntp -= 3155673600
			if ntp > 0: # Correct time 
				from time import localtime
				
				ntp += gmt*3600 #GMT time
				_TimerInfo[2] = (time(),ntp)
				print('Synced ' , localtime(ntp))
				
		except:
			print('Redo')
			AddTask(function=sync_clock,mode='once',period = 10000)
			return 
			
	from time import mktime , ticks_ms
	for i in range(len(ScheduleList)):
		date,month,year = map(int,ScheduleList[i-1]['date'].split('/'))
		hour,minute,second = map(int,ScheduleList[i-1]['time'].split(':'))
		ntptime = mktime([year,month,date,hour,minute,second,0,0])
		print('Attttttttttttt' , ntptime - clock() )
		print('SCHEDULE TASK sex')
		if ntptime < _TimerInfo[2][1] :
			print('Too Late')
			continue 
		print('SCHEDULE TASK FUCKED')
		AddTask(function = ScheduleList[i-1]['function'],name = ScheduleList[i-1]['name'],	mode= 'once',period =  (ntptime - clock())*1000)
		print('SCHEDULE TASK ADDED')
	ScheduleList.clear()
	TaskList.sort()
	
	if len(TaskList) == 0 :
		_TimerInfo[3] = _TimerInfo[1] + 300000 # Call itself every 5 minutes
		_TimerInfo[4] = False
	else :
		if TaskList[0][0] - _TimerInfo[1] < 0 :
			_TimerInfo[3] = _TimerInfo[1] + 1
			_TimerInfo[4] = True
		else :
			if TaskList[0][0] - _TimerInfo[1] > 300000:
				_TimerInfo[3] = _TimerInfo[1] + 300000
				_TimerInfo[4] = False
			else :
				_TimerInfo[3] = _TimerInfo[1] + (TaskList[0][0]-_TimerInfo[1])
				_TimerInfo[4] = True
	global _Tasker
	_Tasker.init(period = _TimerInfo[3]-_TimerInfo[1] , mode = Timer.ONE_SHOT , callback = _TaskHandler)
      
