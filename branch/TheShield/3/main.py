from _thread import start_new_thread
import os, machine, ujson, json, time, utime, network, gc, esp, sys, re, binascii
from machine import Pin, Timer
import usocket as socket
import ustruct as struct
from neopixel import NeoPixel
from Blocky.Blocky import *
LED_PIN = 5
CONFIG_PIN = 12

BROKER = 'broker.getblocky.com'
CHIP_ID = binascii.hexlify(machine.unique_id()).decode('ascii')

#######################################################
# Start main code here
#######################################################
esp.osdebug(None)

def blink_status_led(t):
  global status_led_on
  status_led_on = 1 - status_led_on
  if status_led_on:
    status_led.fill((255, 0, 0))
  else:
    status_led.fill((0, 0, 0))
  status_led.write()
    

def run_user_code():
  error = False
  try:
    global network
    print('1')
    #user_code.bl = network
    exec(open('./user_code.py').read(),globals())
    print('2')
   
    #user_code.network = network
    print('3')

  except Exception as err:
    print('User code crashed. Error: %s' % err)
    network.log('Code crashed. Error: %s' % err)
    error = True
  if error:
    print('Revert to default code')
    network.log('Revert to default code')
    gc.collect()
    print(gc.mem_free())
    try:
      while True:
        network.process()
        time.sleep_ms(100)
    except:
      machine.reset()

config_btn = Pin(CONFIG_PIN, Pin.IN)

status_led = NeoPixel(Pin(LED_PIN, Pin.OUT), 1, timing = True)

if config_btn.value(): 
  print('config button is pressed')
  # turn on config led
  status_led.fill((255, 0, 0))
  status_led.write()
  
  # start while loop until btn is released
  press_begin = time.ticks_ms()
  press_duration = 0
  while config_btn.value():
    press_end = time.ticks_ms()
    press_duration = time.ticks_diff(press_end, press_begin)
    print(press_duration)
    if press_duration > 2000:
      break
    time.sleep_ms(100)
  
  # check how long it was pressed
  if press_duration > 2000:    
    # if more than 3 seconds => flash led many times and copy original user code file and reset
    print('Config button pressed longer than 3 seconds')
    for i in range(10) :
      #status_led.value(1)
      status_led.fill((255, 0, 0))
      status_led.write()
      time.sleep_ms(100)
      #status_led.value(0)
      status_led.fill((0, 0, 0))
      status_led.write()
      time.sleep_ms(100)
    os.remove('user_code.py')
    machine.reset()
  else: # in case pressed less than 1 seconds 
    print('Config button pressed less than 3 seconds')
    import config_manager

else: # config btn is not pressed
  status_led_on = 0
  status_led_blink_timer = Timer(1)
  status_led_blink_timer.init(period=500, mode=Timer.PERIODIC, callback=blink_status_led)

  # load config file
  config = {}
  try:
    f = open('config.json', 'r')
    config = ujson.loads(f.read())
    f.close()
  except Exception:
    print('Failed to load config file')

  #print(config)
  # if error found or missing information => start config mode
  if not config.get('device_name', False) \
    or not config.get('auth_key', False) \
    or not config.get('known_networks', False):
    print('Missing required info in config. Enter config mode')
    status_led_blink_timer.deinit()
    import config_manager
  else:
    print('Finish loading config file')
    #print(config)
    
    # connect to wifi using known network
    print('Connecting to WIFI')    
    wlan_sta = network.WLAN(network.STA_IF)    
    wlan_sta.active(True)
    
    # scan what WIFI network available
    available_wifi = []
    for wifi in wlan_sta.scan():
      available_wifi.append(wifi[0].decode("utf-8"))

    # Go over the preferred networks that are available, attempting first items or moving on if n/a
    for preference in [p for p in config['known_networks'] if p['ssid'] in available_wifi]:
      print("connecting to network {0}...".format(preference['ssid']))
      wlan_sta.connect(preference['ssid'], preference['password'])
      for check in range(0, 50):  # Wait a maximum of 10 times (10 * 500ms = 5 seconds) for success
        if wlan_sta.isconnected():
          break
        time.sleep_ms(100)
      
      if wlan_sta.isconnected():
        break

    if wlan_sta.isconnected():
      print("Connected to Wifi. IP: " + str(wlan_sta.ifconfig()))
      # start network
      network = Blocky(config)
      if not network.connect(): # connect to server
        print('Failed to connect to broker. Enter config mode')
        status_led_blink_timer.deinit()
        status_led.fill((0, 0, 0))
        status_led.write()
        gc.collect()
        import config_manager
      else: # run user code
        status_led_blink_timer.deinit()
        status_led.fill((0, 0, 0))
        status_led.write()
        gc.collect()
        print(gc.mem_free())
        run_user_code() # no thread here , thread kill timer !
    else: # failed to connect to wifi
      print('Failed to connect to Wifi')
      status_led_blink_timer.deinit()
      import config_manager





