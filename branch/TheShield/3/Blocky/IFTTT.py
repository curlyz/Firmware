import urequests

class IFTTT:
	def __init__ (self,key):
		self.key = key 
	def send(self,topic,data=None):
		try :
			urequests.get('https://maker.ifttt.com/trigger/' + topic + '/with/key/'+self.key)
		except:
			pass
			

