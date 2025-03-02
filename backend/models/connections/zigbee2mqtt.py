from fastapi import Depends, APIRouter, Query
from utils.auth import RoleChecker
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
from datetime import datetime


def collect_port(port, device_id, mode) -> DbPorts:
  db_port = DbPorts()
  db_port.device_id = device_id
  db_port.created_by = 0
  db_port.mode = mode
  if 'features' in port and len(port['features']) > 0:
    port.update(port['features'][0])
  for key, value in port.items():
    if hasattr(db_port, key):
      setattr(db_port, key, value)
  db_port.code = port['property']
  db_port.values_variant = port.get('values')
  if db_port.type == 'binary':
    db_port.values_variant = [port.get('value_off'), port.get('value_on')]
  if db_port.type == 'switch':
    db_port.values_variant = [port.get('value_off'), port.get('value_toggle'), port.get('value_on')]
  if 'value_max' in port or 'value_min' in port:
    db_port.values_variant = [port.get('value_min'), port.get('value_max')]
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

  def __init__(self, **kwargs):
    _id = kwargs.get('id', None)
    self._id = _id
    self.connectors_list[_id] = self
    print('zigbee2MqttClass initialized', id(self), kwargs)
    if 'params' in kwargs:
      self.base_topic = kwargs['params']['base_topic']

    self.connect_params = kwargs
    self.mqttc = mqtt.Client(f'server_client_zigbee2mqtt_{id(self)}')
    self.mqttc.on_disconnect = self.on_disconnect
    self.mqttc.on_connect = self.on_connect
    self.mqttc.on_message = self.on_message

    self.massage_maps = {
      'bridge': self.bridge_message,
    }

  def start(self):
    print('zigbee2MqttClass start', id(self))
    self.mqttc.connect(self.connect_params['host'], self.connect_params['port'], 60)
    self.mqttc.subscribe(f"{self.base_topic}/#")
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

  def push_message(self, topic: str, message: dict):
    self.mqttc.publish(f"{self.base_topic}/{topic}", json.dumps(message))

  def get_status(self):
    return self._status

  def send_value(self, device, port, value: str):
    self.push_message(f'{device.code}/set', {port.code: value})

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
    self._status = "connected" if self._status == 'disconnected' else self._status

  def on_disconnect(self, mqttc, obj, rc):
    self._status = "disconnected"

  def on_message(self, mqttc, obj, msg):
    topic = msg.topic[len(self.base_topic) + 1:]
    try:
      message = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
      print('msg:', topic, msg.payload.decode())
      return
    parts = topic.split('/')
    if parts[0] in self.massage_maps:
      self.massage_maps[parts[0]]('/'.join(topic.split('/')[1:]), message)
      return

    if parts[0] in self._devices and len(parts) == 1:
      self.values[parts[0]] = self.values.get(parts[0], {})

      change_values = {key: value for key, value in message.items() if value != self.values[parts[0]].get(key)}
      if not change_values:
        return
      self.values[parts[0]] = message
      for key, value in change_values.items():
        self._devices[parts[0]].income_value(key, value)

  def bridge_message(self, path, message):
    if path == 'state' and 'state' in message:
      self._status = message['state']
      return

    if path == 'info':
      keys = ['permit_join', 'permit_join_timeout', 'network', 'version']
      for key in keys:
        if key in message:
          setattr(self, key, message[key])

    if path == 'devices':
      for device in message:
        ieee = device['ieee_address']
        item = {
          'code': ieee,
          'type': device['type'],
          'network_address': device['network_address'],
          'name': device.get('friendly_name', ieee),
          'description': (device.get('definition') or {}).get('description', ''),
          'model': (device.get('definition') or {}).get('model', ''),
          'vendor': (device.get('definition') or {}).get('vendor', ''),
        }

        if ieee not in self._devices:
          # save to db
          db = db_session()
          db_device = DbDevices()
          db_device.connection_id = self._id
          db_device.created_by = 0
          for key, value in item.items():
            if hasattr(db_device, key):
              setattr(db_device, key, value)
          db.add(db_device)
          db.commit()

          item = db.query(DbDevices).filter(DbDevices.id == db_device.id).first()
          Devices().add_device(item)

          ports = []
          # save ports
          modes = ['exposes', 'options']
          for mode in modes:
            for port in ((device.get('definition') or {}).get(mode) or []):
              db_port = collect_port(port, db_device.id, mode)
              db.add(db_port)
              ports.append(db_port.id)
          db.commit()

          ports = db.query(DbPorts).filter(DbPorts.id.in_(ports)).all()
          for port in ports:
            Devices().add_port(port)


def add_routes(app):
  print('Adding ZIGBEE 2 MQTT routes')

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

    if not device_id in zigbee2mqtt._devices and device_id.isdigit():
      device_id = int(device_id)
      for key, device in zigbee2mqtt._devices.items():
        if device.id == device_id:
          device_id = key
          break
      else:
        return {"status": 'error', "message": 'Device not found'}
    zigbee2mqtt.refresh_params(device_id)
    return {"status": 'ok'}
