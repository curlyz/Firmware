
class Network:
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
