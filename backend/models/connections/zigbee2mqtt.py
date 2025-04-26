from fastapi import Depends, APIRouter, Query, HTTPException
from utils.auth import RoleChecker, CurrentUser
import paho.mqtt.client as mqtt
import json
from pprint import pprint
from typing import Optional, Union
from utils.db_utils import db_session
from db_models.devices import Devices as DbDevices
from db_models.ports import Ports as DbPorts
from models.connections import Connectors
from models.devices import Devices
import threading
from datetime import datetime, timedelta
from utils.logs import log_print
from utils.socket_utils import connection_manager
from time import sleep
from queue import Queue, Empty
from db_models.port_metadata import PortMetadata


def collect_port(port, device_id, mode, db_port: DbPorts = None, user_id: int = None) -> DbPorts:
  db_port = db_port or DbPorts()
  db_port.device_id = device_id
  db_port.created_by = db_port.created_by or user_id
  db_port.updated_by = user_id
  db_port.mode = port.get('category') or mode
  if 'features' in port and len(port['features']) > 0:
    port.update(port['features'][0])
  if 'endpoint' in port:
    port['label'] = f"{port['label'] or ''} ({port['endpoint']})"
  for key, value in port.items():
    if hasattr(db_port, key) and not getattr(db_port, key):
      setattr(db_port, key, value)

  db_port.code = port['property']
  db_port.values_variant = port.get('values')
  if db_port.type == 'binary':
    db_port.values_variant = [port.get('value_off'), port.get('value_on')]
  if db_port.type == 'switch':
    db_port.values_variant = [port.get('value_off'), port.get('value_toggle'), port.get('value_on')]
  if 'value_max' in port or 'value_min' in port:
    db_port.values_variant = [port.get('value_min'), port.get('value_max')]

  if not db_port.metadata_id:
    meta = PortMetadata().find_match(db_port.code)
    if meta:
      db_port.metadata_id = meta.id
  return db_port


class Zigbee2mqttClass:
  type = 'zigbee2mqtt'
  base_topic = 'zigbee2mqtt'
  connectors_list = {}
  mqttc: mqtt.Client = None
  _status: str = "disconnected"
  _devices: dict = {}
  permit_join: bool = False
  permit_join_timeout: int = 0
  network: dict = {}
  version: str = ''
  values = {}
  last_msg_time: datetime = None

  last_devices: dict = {}

  params = {
    'host': {
      'type': 'string',
      'description': 'Host address of the MQTT broker',
      'default': 'localhost',
      'required': True,
    },
    'port': {
      'type': 'integer',
      'description': 'Port of the MQTT broker',
      'default': 1883,
      'required': True,
    },
    'base_topic': {
      'type': 'string',
      'description': 'Base topic for Zigbee2MQTT',
      'default': 'zigbee2mqtt',
      'required': True,
    },
    'username': {
      'type': 'string',
      'description': 'Username for MQTT broker',
      'default': '',
    },
    'password': {
      'type': 'string',
      'description': 'Password for MQTT broker',
      'default': '',
    },
    'auto_load_devices': {
      'type': 'bool',
      'default': True,
      'description': 'Auto load new devices from Zigbee2MQTT',
    }
  }

  rules = {
    "allow_device_edit": False,
    "allow_device_add": False,
    "allow_device_delete": False,
    "allow_port_edit": False,
    "allow_port_add": False,
    "allow_port_delete": False
  }

  actions = [
    {
      "name": "bind",
      "type": "request",
      "scope": "connection",
      "icon": "bind",
      "endpoint": "/api/devices/{device_id}/restart",
      "method": "POST",
      "confirm": True,
      "input": {
        "delay": {
          "type": "int",
          "label": "На сколько минут?(0 - бесконечно)",
          "default": 5,
          "min": 0,
          "max": 60,
        }
      }
    },
    {
      'name': 'update device',
      'type': 'request',
      'scope': 'connection',
      'icon': 'refresh-auto',
      "method": "GET",
      'endpoint': '/api/live/connections/{connection_id}/zigbee2mqtt/request/all',
      "update_after": "table.devices|table.ports",
    },
    {
      "name": "Состояние",
      "type": "state",
      "scope": "connection",
      "icon": "mdi-access-point",
      "key": "status",  # from live[connection_id]['status']
      "show_if_empty": False
    },
    {
      "name": "code",
      "type": "state",
      "scope": "device",
      "color": "orange",
      "icon": "code-tags",
      "key": "code",  # from device[params][ip]
      "show_if_empty": False
    },
    {
      "name": "code",
      "type": "state",
      "scope": "device",
      "color": "blue",
      "icon": "network",
      "key": "type",  # from device[params][ip]
      "show_if_empty": False
    },
    {
      "name": "update",
      "type": "request",
      "scope": "device",
      "method": "GET",
      "icon": "refresh",
      "endpoint": "/api/live/connections/{connection_id}/zigbee2mqtt/request/{device_id}",
      "update_after": "table.devices|table.ports",
    }
  ]

  def __init__(self, **kwargs):
    _id = kwargs.get('id', None)
    self._id = _id
    self.connectors_list[_id] = self
    log_print('zigbee2MqttClass initialized', id(self), kwargs)
    if 'params' in kwargs:
      self.base_topic = kwargs['params'].get('base_topic', 'zigbee2mqtt')
      if self.base_topic[-1] == '/':
        self.base_topic = self.base_topic[:-1]

    self.connect_params = kwargs
    self.mqttc = mqtt.Client(f'server_client_zigbee2mqtt_{id(self)}')
    self.mqttc.on_disconnect = self.on_disconnect
    self.mqttc.on_connect = self.on_connect
    self.mqttc.on_message = self.on_message

    self.message_maps = {
      'bridge': self.bridge_message,
    }

    self.publish_queue = Queue()
    self.start_publisher()

    self.start_ping_loop()

  def load_device_image(self):
    # https: // www.zigbee2mqtt.io / images / devices / TS011F_plug_1.jpg
    pass

  def update_device_info(self,
                         device_id: Optional[str] = None,
                         ieee: Optional[str] = None,
                         only_new: bool = True,
                         user_id: Optional[int] = None) -> Optional[bool]:
    if device_id is None and ieee is None:
      return None

    first_init = False
    with (db_session() as db):
      db_device = db.query(DbDevices).filter(DbDevices.connection_id == self._id)
      if ieee is not None:
        db_device = db_device.filter(DbDevices.code == ieee)
      if device_id is not None:
        db_device = db_device.filter(DbDevices.id == device_id)
      db_device = db_device.first()
      if not db_device:
        first_init = True
        if ieee is None:
          return None
        db_device = DbDevices()
        db_device.connection_id = self._id
        db_device.created_by = user_id
        db_device.code = ieee
      else:
        if only_new:
          return None
        ieee = db_device.code

    if ieee not in self.last_devices:
      return None

    device = self.last_devices[ieee]
    if device['type'] == 'Coordinator':
      return None

    with db_session() as db:
      db_device.updated_by = user_id
      db_device.type = db_device.type or device['type']
      db_device.name = db_device.name or device.get('friendly_name', ieee)
      db_device.description = db_device.description or (device.get('definition') or {}).get('description', '')
      db_device.model = db_device.model or (device.get('definition') or {}).get('model', '')
      db_device.vendor = db_device.vendor or (device.get('definition') or {}).get('vendor', '')
      db_device.params = db_device.params or {}
      db_device.params['network_address'] = device.get('network_address', '')
      db_device.params['power_source'] = device.get('power_source', '')
      db_device.params['endpoints'] = device.get('endpoints', '')
      db.add(db_device)
      db.commit()

      item = db.query(DbDevices).filter(DbDevices.id == db_device.id).first()
      Devices().add_device(item.__dict__)

      db_ports = {}
      if not first_init:
        db_ports = {port.code: port for port in db.query(DbPorts).filter(DbPorts.device_id == db_device.id).all()}
      ports = []
      # save ports
      modes = ['exposes', 'options']
      for mode in modes:
        for port in ((device.get('definition') or {}).get(mode) or []):
          port_property = port.get('property') or port.get('features', [{}])[0].get('property')
          db_port = collect_port(port, db_device.id, mode, db_ports.get(port_property), user_id)
          db.add(db_port)
          ports.append(db_port)
      db.commit()

      ports = [port.id for port in ports]
      ports = db.query(DbPorts).filter(DbPorts.id.in_(ports)).all()
      for port in ports:
        Devices().add_port(port)

    return True

  def start_publisher(self):
    def publisher_loop():
      while True:
        try:
          topic, message = self.publish_queue.get(timeout=1)
          if self._status == 'connected':
            self.mqttc.publish(f"{self.base_topic}/{topic}", json.dumps(message))
          else:
            # повторим позже
            self.publish_queue.put((topic, message))
            sleep(1)
        except Empty:
          continue
        except Exception as e:
          log_print(f"[zigbee2mqtt_MQTT_MQTT] Publish error: {e}")

    threading.Thread(target=publisher_loop, daemon=True).start()

  def start_ping_loop(self):
    self.last_msg_time = datetime.now()

    def ping_loop():
      while True:
        if self._status == 'connected':
          if self.last_msg_time + timedelta(seconds=30) < datetime.now():
            self.push_message('bridge/ping', {}, queue=False)
          if self.last_msg_time + timedelta(seconds=60) < datetime.now():
            self._status = 'disconnected'
            self.mqttc.loop_stop()
            self.mqttc.disconnect()
            self.mqttc.reconnect()
        sleep(30)

    threading.Thread(target=ping_loop, daemon=True).start()

  def start(self):
    log_print('zigbee2MqttClass start', id(self))
    self.mqttc.connect(self.connect_params['host'], self.connect_params['port'], 60)
    self.mqttc.loop_start()

  def __del__(self):
    if self.mqttc:
      self.mqttc.loop_stop()
      self.mqttc.disconnect()

  def add_device(self, device):
    if device.code not in self._devices:
      threading.Timer(2, lambda x: self.refresh_params(x), args=[device.code]).start()
    self._devices[device.code] = device

  def refresh_params(self, device_id):
    params = {
      port.code: "" for port in self._devices[device_id].ports.values()
    }
    if not params:
      return
    self.push_message(f'{device_id}/get', params)

  def push_message(self, topic: str, message: dict, queue: bool = True):
    topic = f"{self.base_topic}/{topic}"
    if queue:
      self.publish_queue.put((topic, message))
    elif self._status == 'connected':
      try:
        self.mqttc.publish(topic, json.dumps(message))
      except Exception as e:
        log_print(f"[zigbee2mqtt_MQTT] Publish error on topic {topic}: {e}")

  def get_status(self):
    return self._status

  def send_value(self, device, port, value: str):
    self.push_message(f'{device.code}/set', {port.code: value})
    connection_manager.broadcast_log(text='Zigbee2mqtt set value',
                                     level='debug',
                                     device_id=device.id,
                                     permission='root',
                                     direction='out', )

  def get_info(self):
    return {'status': self._status,
            'host': self.mqttc._host,
            'port': self.mqttc._port,
            'client_id': self.mqttc._client_id,
            'base_topic': self.base_topic,
            'type': 'zigbee2mqtt',
            'device_count': len(self._devices),
            'permit_join': self.permit_join if not self.permit_join else self.permit_join_timeout,
            'network': self.network,
            'version': self.version}

  def on_connect(self, mqttc, obj, flags, reason_code):
    if reason_code == 0:
      self._status = "connected"
      log_print(f"[zigbee2mqtt_MQTT] Connected to {self.connect_params['host']}:{self.connect_params['port']}")
      mqttc.subscribe(f"{self.base_topic}/#")
      log_print(f"[zigbee2mqtt_MQTT] Subscribed to {self.base_topic}/#")
    else:
      log_print(f"[zigbee2mqtt_MQTT] Connection failed: {reason_code}")
      self.reconnect()

  def on_disconnect(self, mqttc, obj, rc):
    self._status = "disconnected"
    log_print(f"[zigbee2mqtt_MQTT] Disconnected with code {rc}")
    if rc != 0:
      log_print("[zigbee2mqtt_MQTT] Unexpected disconnect. Trying to reconnect...")
      self.reconnect()

  def reconnect(self):
    def _reconnect():
      while self._status != "connected":
        try:
          self.mqttc.reconnect()
          log_print("[zigbee2mqtt_MQTT] Reconnected successfully")
          break
        except Exception as e:
          log_print(f"[zigbee2mqtt_MQTT] Reconnect failed: {e}")
          sleep(5)

    threading.Thread(target=_reconnect, daemon=True).start()

  def on_message(self, mqttc, obj, msg):
    self.last_msg_time = datetime.now()

    topic = msg.topic[len(self.base_topic) + 1:]
    try:
      message = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
      log_print('msg:', topic, msg.payload.decode())
      return
    parts = topic.split('/')
    if parts[0] in self.message_maps:
      self.message_maps[parts[0]]('/'.join(topic.split('/')[1:]), message)
      return

    if parts[0] in self._devices and len(parts) == 1:
      self.values[parts[0]] = self.values.get(parts[0], {})

      # change_values = {key: value for key, value in message.items() if value != self.values[parts[0]].get(key)}
      change_values = message
      connection_manager.broadcast_log(text='Zigbee2mqtt get value',
                                       level='debug',
                                       device_id=self._devices[parts[0]].id,
                                       permission='root',
                                       direction='in',
                                       value=change_values)
      # if not change_values:
      #   return
      self.values[parts[0]] = message
      for key, value in change_values.items():
        self._devices[parts[0]].income_value(key, value)

  def bridge_message(self, path, message):
    if path == 'pong':
      log_print('[zigbee2mqtt_MQTT] Pong received')

    if path == 'state' and 'state' in message:
      self._status = message['state']
      return

    if path == 'info':
      keys = ['permit_join', 'permit_join_timeout', 'network', 'version']
      for key in keys:
        if key in message:
          setattr(self, key, message[key])

    if path == 'devices':
      self.last_devices = {}
      for device in message:
        self.last_devices[device['ieee_address']] = device
        self.update_device_info(ieee=device['ieee_address'], only_new=True)


def add_routes(app):
  log_print('Adding ZIGBEE 2 MQTT routes')

  def get_connection(connector_id: int):
    connections = Connectors()
    connector_id = int(connector_id)
    if connector_id not in connections.connectors:
      return None
    return connections.connectors[connector_id]

  @app.get("/api/live/connections/{connector_id}/zigbee2mqtt",
           tags=["live/connections/zigbee2mqtt"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def get_zigbee2mqtt_info(connector_id: int):
    zigbee2mqtt = get_connection(connector_id)
    if not zigbee2mqtt:
      return {"status": 'error', "message": 'Connector not found'}
    return zigbee2mqtt.get_info()

  @app.get("/api/live/connections/{connector_id}/zigbee2mqtt/permit_join",
           tags=["live/connections/zigbee2mqtt"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def get_zigbee2mqtt_permit_join(connector_id: int, time_seconds: Union[int, None] = 250):
    zigbee2mqtt = get_connection(connector_id)
    if not zigbee2mqtt:
      return {"status": 'error', "message": 'Connector not found'}
    zigbee2mqtt.push_message('bridge/request/permit_join', {'time': time_seconds, 'value': bool(time_seconds)})
    return {"status": 'ok'}

  @app.get("/api/live/connections/{connector_id}/zigbee2mqtt/request/networkmap",
           tags=["live/connections/zigbee2mqtt"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def request_zigbee2mqtt_request_networkmap(connector_id: int):
    zigbee2mqtt = get_connection(connector_id)
    if not zigbee2mqtt:
      return {"status": 'error', "message": 'Connector not found'}
    zigbee2mqtt.push_message('bridge/request/networkmap', {"type": "raw", "routes": True})
    return {"status": 'ok'}

  @app.get("/api/live/connections/{connector_id}/zigbee2mqtt/refresh_params",
           tags=["live/connections/zigbee2mqtt"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def refresh_zigbee2mqtt_params(connector_id: int, device_id: str):
    zigbee2mqtt = get_connection(connector_id)
    if not zigbee2mqtt:
      return {"status": 'error', "message": 'Connector not found'}

    if device_id not in zigbee2mqtt._devices and device_id.isdigit():
      device_id = int(device_id)
      for key, device in zigbee2mqtt._devices.items():
        if device.id == device_id:
          device_id = key
          break
      else:
        return {"status": 'error', "message": 'Device not found'}
    zigbee2mqtt.refresh_params(device_id)
    return {"status": 'ok'}

  @app.get("/api/live/connections/{connector_id}/zigbee2mqtt/request/all",
           tags=["live/connections/zigbee2mqtt"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def request_zigbee2mqtt_request_all(connector_id: int):
    zigbee2mqtt = get_connection(connector_id)
    if not zigbee2mqtt:
      return {"status": 'error', "message": 'Connector not found'}

    for device in zigbee2mqtt._devices.values():
      zigbee2mqtt.update_device_info(device_id=device.id, only_new=False)

    return {"status": 'ok'}

  @app.get("/api/live/connections/{connector_id}/zigbee2mqtt/request/{device_id}",
           tags=["live/connections/zigbee2mqtt"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def request_zigbee2mqtt_request_device(connector_id: int, device_id: str, current_user: CurrentUser):
    zigbee2mqtt = get_connection(connector_id)
    if not zigbee2mqtt:
      return {"status": 'error', "message": 'Connector not found'}

    if device_id in zigbee2mqtt._devices:
      device_id = zigbee2mqtt._devices[device_id].id
    elif not device_id.isdigit():
      return {"status": 'error', "message": 'Device not found'}
    else:
      device_id = int(device_id)

    return {"status": 'ok', 'data': zigbee2mqtt.update_device_info(device_id=device_id,
                                                                   only_new=False,
                                                                   user_id=current_user.id)}
