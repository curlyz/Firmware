import machine
import network
import socket
import time
import random
import json, ujson, binascii, gc
from machine import Pin
from neopixel import NeoPixel

#from microWebSrv import MicroWebSrv

from    json        import dumps
from    os          import stat
from    _thread     import start_new_thread
import  socket
import  gc

try :
    from microWebTemplate import MicroWebTemplate
except :
    pass

try :
    from microWebSocket import MicroWebSocket
except :
    pass

from Blocky.MicroWebSrv import MicroWebSrv

    # ============================================================================
    # ============================================================================
    # ============================================================================



class ConfigManager:
  def __init__(self, config={}):
    self.config = config
    self.np = NeoPixel(Pin(5, Pin.OUT), 1, timing = True)
    self.np.fill((255, 0, 0)); self.np.write()

    self.wlan_ap = network.WLAN(network.AP_IF)
    self.wlan_sta = network.WLAN(network.STA_IF)

    # setup for ssid
    if self.config.get('device_name'):
      self.ap_name= self.config['device_name']
    else:
      self.ap_name= "BlockyWifi_" + binascii.hexlify(machine.unique_id()).decode('ascii')
    self.ap_password = "12345678"

    self.wifi_status = 0
    
  def connect(self, ssid, password):
    self.wlan_sta.active(True)
    self.wlan_sta.connect(ssid, password)
    a=0
    print('Connecting to wifi')
    while not self.wlan_sta.isconnected() | (a > 99) :
      time.sleep(0.1)
      a+=1
      print('.', end='')
    
    if self.wlan_sta.isconnected():
      print('\nConnected. Network config:', self.wlan_sta.ifconfig())
      self.wifi_status = 1
      return True
    else : 
      print('\nProblem. Failed to connect to :' + ssid)
      self.wifi_status = 2
      self.wlan_sta.active(False)
      return False

  def _httpHandlerIndexGet(self, httpClient, httpResponse):
    print('Get index request')  
    htmlFile = open('index.html', 'r')
    content = ''
    for line in htmlFile:
      print(line)
      content = content + line
    httpResponse.WriteResponseOk( headers = None,
      contentType	 = "text/html",	contentCharset = "UTF-8",	content = content)
  
  def _httpHandlerCheckStatus(self, httpClient, httpResponse):
    print('Get check status request')
    if self.wifi_status == 1:
      content = 'OK'
    elif self.wifi_status == 2:
      content = 'Failed'
    else:  
      content = ''
    
    httpResponse.WriteResponseOk(headers = None,
      contentType	 = "text/html",
      contentCharset = "UTF-8",
      content = content)
      
    if self.wifi_status == 1:
      print('Wait for rebooting')
      time.sleep(5)
      print('Rebooting')
      machine.reset()

  def _httpHandlerSaveConfig(self, httpClient, httpResponse):
    print('Get save config request')
    request_json = ujson.loads(httpClient.ReadRequestContent().decode('ascii'))
    self.wifi_status = 0
    print(request_json)
    httpResponse.WriteResponseOk(headers = None,
      contentType	 = "text/html",
      contentCharset = "UTF-8",
      content = 'OK')
    
    if self.connect(request_json['ssid'], request_json['password']):
      # save config
      if not self.config.get('known_networks'):
        self.config['known_networks'] = [{'ssid': request_json['ssid'], 'password': request_json['password']}]
      else:
        exist_ssid = None
        for n in self.config['known_networks']:
          if n['ssid'] == request_json['ssid']:
            exist_ssid = n
            break
        if exist_ssid:
          exist_ssid['password'] = request_json['password'] # update WIFI password
        else:
          # add new WIFI network
          self.config['known_networks'].append({'ssid': request_json['ssid'], 'password': request_json['password']})
      
      self.config['device_name'] = request_json['deviceName']
      self.config['auth_key'] = request_json['authKey']
      f = open('config.json', 'w')
      f.write(ujson.dumps(self.config))
      f.close()
    
  def is_ascii(self, s):
    return all(ord(c) < 128 for c in s)
  
  def _httpHandlerScanNetworks(self, httpClient, httpResponse) :
    print('Receive request to scan networks')
    self.wlan_sta.active(True)
    networks = []
    for nw in self.wlan_sta.scan():
      if (self.is_ascii(nw[0].decode('ascii'))):
        networks.append({'ssid': nw[0].decode('ascii'), 'rssi': nw[3]})
      else:
        print('Unicode error found in WiFi SSID')
        continue
    
    content = ujson.dumps(networks)
   
    httpResponse.WriteResponseOk(headers = None,
      contentType	= "application/json",
      contentCharset = "UTF-8",
      content = content)
                   
  def start(self):    
    self.wlan_sta.active(True)
    self.wlan_ap.active(True)

    self.wlan_ap.config(essid=self.ap_name, password=self.ap_password)

    routeHandlers = [
      ("/", "GET", self._httpHandlerIndexGet),
      ("/aplist", "GET", self._httpHandlerScanNetworks),
      ("/status", "GET", self._httpHandlerCheckStatus),
      ("/save", "POST",	self._httpHandlerSaveConfig)
    ]

    srv = MicroWebSrv(routeHandlers=routeHandlers)
    srv.Start(threaded=True)

    print('Now enter config mode')
    print('Connect to Wifi ssid :' + self.ap_name + ' , default pass: ' + self.ap_password)
    print('And connect to Blocky via at 192.168.4.1')

    gc.collect()
    print(gc.mem_free())

    return True
    
print('Loading config file')
config = {}
try:
  f = open('config.json', 'r')
  config = ujson.loads(f.read())
  f.close()
except Exception as err:
  print('Failed to load config file')
  print(err)

configManager = ConfigManager(config)

if configManager.start():
  	
  # Main Code is here
  print ("ESP OK")
  # to import your code;
  # import sample_mqtt.py

else:
  print ("There is something wrong")




