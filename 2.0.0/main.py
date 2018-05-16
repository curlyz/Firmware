from _thread import start_new_thread
import os, machine, ujson, json, time, utime, network, gc, esp, sys, re, binascii
from machine import Pin, Timer
import usocket as socket
import ustruct as struct
from neopixel import NeoPixel

LED_PIN = 5
CONFIG_PIN = 12

BROKER = 'broker.getblocky.com'
CHIP_ID = binascii.hexlify(machine.unique_id()).decode('ascii')

class MQTTException(Exception):
    pass

class MQTTClient:

  def __init__(self, client_id, server, port=0, user=None, password=None, keepalive=0,ssl=False, ssl_params={}):
    if port == 0:
      port = 8883 if ssl else 1883
    self.client_id = client_id
    self.sock = None
    self.addr = socket.getaddrinfo(server, port)[0][-1]
    self.ssl = ssl
    self.ssl_params = ssl_params
    self.pid = 0
    self.cb = None
    self.user = user
    self.pswd = password
    self.keepalive = keepalive
    self.lw_topic = None
    self.lw_msg = None
    self.lw_qos = 0
    self.lw_retain = False

  def _send_str(self, s):
    self.sock.write(struct.pack("!H", len(s)))
    self.sock.write(s)

  def _recv_len(self):
    n = 0
    sh = 0
    while 1:
      b = self.sock.read(1)[0]
      n |= (b & 0x7f) << sh
      if not b & 0x80:
        return n
      sh += 7

  def set_callback(self, f):
    self.cb = f

  def set_last_will(self, topic, msg, retain=False, qos=0):
    assert 0 <= qos <= 2
    assert topic
    self.lw_topic = topic
    self.lw_msg = msg
    self.lw_qos = qos
    self.lw_retain = retain

  def connect(self, clean_session=True):
    self.sock = socket.socket()
    self.sock.connect(self.addr)
    if self.ssl:
      import ussl
      self.sock = ussl.wrap_socket(self.sock, **self.ssl_params)
    msg = bytearray(b"\x10\0\0\x04MQTT\x04\x02\0\0")
    msg[1] = 10 + 2 + len(self.client_id)
    msg[9] = clean_session << 1
    if self.user is not None:
      msg[1] += 2 + len(self.user) + 2 + len(self.pswd)
      msg[9] |= 0xC0
    if self.keepalive:
      assert self.keepalive < 65536
      msg[10] |= self.keepalive >> 8
      msg[11] |= self.keepalive & 0x00FF
    if self.lw_topic:
      msg[1] += 2 + len(self.lw_topic) + 2 + len(self.lw_msg)
      msg[9] |= 0x4 | (self.lw_qos & 0x1) << 3 | (self.lw_qos & 0x2) << 3
      msg[9] |= self.lw_retain << 5
    self.sock.write(msg)
    #print(hex(len(msg)), hexlify(msg, ":"))
    self._send_str(self.client_id)
    if self.lw_topic:
      self._send_str(self.lw_topic)
      self._send_str(self.lw_msg)
    if self.user is not None:
      self._send_str(self.user)
      self._send_str(self.pswd)
    resp = self.sock.read(4)
    assert resp[0] == 0x20 and resp[1] == 0x02
    if resp[3] != 0:
      raise MQTTException(resp[3])
    return resp[2] & 1

  def disconnect(self):
    self.sock.write(b"\xe0\0")
    self.sock.close()

  def ping(self):
    self.sock.write(b"\xc0\0")

  def publish(self, topic, msg, retain=False, qos=0):
    pkt = bytearray(b"\x30\0\0\0")
    pkt[0] |= qos << 1 | retain
    sz = 2 + len(topic) + len(msg)
    if qos > 0:
      sz += 2
    assert sz < 2097152
    i = 1
    while sz > 0x7f:
      pkt[i] = (sz & 0x7f) | 0x80
      sz >>= 7
      i += 1
    pkt[i] = sz
    #print(hex(len(pkt)), hexlify(pkt, ":"))
    self.sock.write(pkt, i + 1)
    self._send_str(topic)
    if qos > 0:
      self.pid += 1
      pid = self.pid
      struct.pack_into("!H", pkt, 0, pid)
      self.sock.write(pkt, 2)
    self.sock.write(msg)
    if qos == 1:
      while 1:
        op = self.wait_msg()
        if op == 0x40:
          sz = self.sock.read(1)
          assert sz == b"\x02"
          rcv_pid = self.sock.read(2)
          rcv_pid = rcv_pid[0] << 8 | rcv_pid[1]
          if pid == rcv_pid:
            return
    elif qos == 2:
      assert 0

  def subscribe(self, topic, qos=0):
    assert self.cb is not None, "Subscribe callback is not set"
    pkt = bytearray(b"\x82\0\0\0")
    self.pid += 1
    struct.pack_into("!BH", pkt, 1, 2 + 2 + len(topic) + 1, self.pid)
    #print(hex(len(pkt)), hexlify(pkt, ":"))
    self.sock.write(pkt)
    self._send_str(topic)
    self.sock.write(qos.to_bytes(1, "little"))
    while 1:
      op = self.wait_msg()
      if op == 0x90:
        resp = self.sock.read(4)
        #print(resp)
        assert resp[1] == pkt[2] and resp[2] == pkt[3]
        if resp[3] == 0x80:
          raise MQTTException(resp[3])
        return

  # Wait for a single incoming MQTT message and process it.
  # Subscribed messages are delivered to a callback previously
  # set by .set_callback() method. Other (internal) MQTT
  # messages processed internally.
  def wait_msg(self):
    res = self.sock.read(1)
    self.sock.setblocking(True)
    if res is None:
      return None
    if res == b"":
      raise OSError(-1)
    if res == b"\xd0":  # PINGRESP
      sz = self.sock.read(1)[0]
      assert sz == 0
      return None
    op = res[0]
    if op & 0xf0 != 0x30:
      return op
    sz = self._recv_len()
    topic_len = self.sock.read(2)
    topic_len = (topic_len[0] << 8) | topic_len[1]
    topic = self.sock.read(topic_len)
    sz -= topic_len + 2
    if op & 6:
      pid = self.sock.read(2)
      pid = pid[0] << 8 | pid[1]
      sz -= 2
    msg = self.sock.read(sz)
    self.cb(topic, msg)
    if op & 6 == 2:
      pkt = bytearray(b"\x40\x02\0\0")
      struct.pack_into("!H", pkt, 2, pid)
      self.sock.write(pkt)
    elif op & 6 == 4:
      assert 0

  # Checks whether a pending message from server is available.
  # If not, returns immediately with None. Otherwise, does
  # the same processing as wait_msg.
  def check_msg(self):
    self.sock.setblocking(False)
    return self.wait_msg()


class Blocky:
  def __init__(self, config):
    self.config = config
    self.state = 0
    self.has_msg = False
    self.topic = ''
    self.msg = ''
    self.mqtt = MQTTClient(CHIP_ID, BROKER, 0, CHIP_ID, self.config['auth_key'], 1883)
    self.message_handlers = {}
      
  def on_message(self, topic, msg):
    print('On new message topic: ' + topic.decode())
    self.has_msg = True
    self.topic = topic.decode()
    self.msg = msg.decode()      
  
  def connect(self):
    print('Connecting to broker')
    self.mqtt.set_callback(self.on_message)
    try:
      self.mqtt.connect()
    except Exception as error:
      print('Failed to connect to broker')
      return False
    
    register_data = {'event': 'register', 
      'chipId': CHIP_ID, 
      'firmwareVersion': '1.0',
      'name': self.config.get('device_name', 'Blocky_' + CHIP_ID),
      'type': 'esp32'
    }
    
    self.mqtt.publish(topic=self.config['auth_key'] + '/sys/', msg=ujson.dumps(register_data))
    self.mqtt.subscribe(self.config['auth_key'] + '/sys/' + CHIP_ID + '/ota/#')
    self.mqtt.subscribe(self.config['auth_key'] + '/sys/' + CHIP_ID + '/run/#')
    self.mqtt.subscribe(self.config['auth_key'] + '/sys/' + CHIP_ID + '/rename/#')
    self.mqtt.subscribe(self.config['auth_key'] + '/sys/' + CHIP_ID + '/reboot/#')
    self.mqtt.subscribe(self.config['auth_key'] + '/sys/' + CHIP_ID + '/upload/#')
    self.mqtt.subscribe(self.config['auth_key'] + '/sys/' + CHIP_ID + '/upgrade/#')
    self.state = 1
    print('Connected to broker')
    return True
    
  def process(self):
    if self.state != 1:
      return
    self.mqtt.check_msg()
    self.handle_msg()
      
    
  def handle_msg(self):
    if not self.has_msg:
      return
    print('Receive new message with topic: ' + self.topic)
    print('Message: ' + self.msg)
    
    sysPrefix = self.config['auth_key'] + '/sys/' + CHIP_ID + '/'
    userPrefix = self.config['auth_key'] + '/user/'
    if self.topic.startswith(sysPrefix):
      if self.topic == sysPrefix + 'ota':
        print('Receive OTA message')
        f = open('user_code.py', 'w')
        f.write(self.msg)
        f.close()
        otaAckMsg = {'chipId': CHIP_ID, 'event': 'ota_ack'}        
        self.mqtt.publish(topic=self.config['auth_key'] + '/sys/', msg=ujson.dumps(otaAckMsg))
        time.sleep_ms(500)
        machine.reset()
      elif self.topic == sysPrefix + 'run':
        print('Receive RUN message')
        exec(self.msg, globals())
        
      elif self.topic == sysPrefix + 'reboot':
        print('Receive REBOOT message')
        machine.reset()
      elif self.topic == sysPrefix + 'upload':
        print('Receive UPLOAD message')
      elif self.topic == sysPrefix + 'upgrade':
        print('Receive UPGRADE message')
    elif self.topic.startswith(userPrefix):
      for t in self.message_handlers:
        format_topic = t.replace('/+', '/[a-zA-Z0-9_]+')
        format_topic = format_topic.replace('/#', '/*')
        if re.match(format_topic, self.topic):
          self.message_handlers.get(t)(self.topic, self.msg)
    self.topic = ''
    self.msg = ''
    self.has_msg = False
    
  def send_message(self, topic, msg):
    if self.state != 1 or not topic or not msg:
      return
    topic = self.config['auth_key'] + '/user/' + topic
    self.mqtt.publish(topic=topic, msg=str(msg))
    
  def log(self, text):
    if self.state != 1 or text is None or text == '':
      return
    sysPrefix = self.config['auth_key'] + '/sys/' + CHIP_ID + '/log'
    self.mqtt.publish(topic=sysPrefix, msg=str(text))
    
  def subscribe(self, topic, cb):
    if self.state != 1 or not topic:
      return
    topic = self.config['auth_key'] + '/user/' + topic
    self.mqtt.subscribe(topic)
    self.message_handlers[topic] = cb

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
    import user_code
    user_code.blocky = blocky
    user_code.setup()
    user_code.loop()
  except Exception as err:
    print('User code crashed. Error: %s' % err)
    blocky.log('Code crashed. Error: %s' % err)
    error = True
  if error:
    print('Revert to default code')
    blocky.log('Revert to default code')
    gc.collect()
    print(gc.mem_free())
    try:
      while True:
        blocky.process()
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
  status_led_blink_timer = Timer(-1)
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
      # start blocky      
      blocky = Blocky(config)
      if not blocky.connect(): # connect to server
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
        start_new_thread(run_user_code, ())
    else: # failed to connect to wifi
      print('Failed to connect to Wifi')
      status_led_blink_timer.deinit()
      import config_manager


