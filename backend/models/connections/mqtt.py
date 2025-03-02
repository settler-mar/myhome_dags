from fastapi import Depends, APIRouter, Query
from utils.auth import RoleChecker
import paho.mqtt.client as mqtt


class MqttClass:
  type = 'mqtt'
  connectors_list = {}
  mqttc: mqtt.Client = None
  _status: str = "disconnected"
  _devices: dict = {}

  def __init__(self, **kwargs):
    _id = kwargs.get('id', None)
    self.connectors_list[_id] = self
    print('MqttClass initialized', id(self), kwargs)

    self.mqttc = mqtt.Client(f'server_client_{id(self)}')
    self.mqttc.on_disconnect = self.on_disconnect
    self.mqttc.on_connect = self.on_connect
    self.mqttc.on_message = self.on_message
    self.mqttc.connect(kwargs['host'], kwargs['port'], 60)
    self.mqttc.subscribe("#")
    self.mqttc.loop_start()

  def __del__(self):
    if self.mqttc:
      self.mqttc.loop_stop()
      self.mqttc.disconnect()

  def add_device(self, device):
    self._devices[device.code] = device

  def get_status(self):
    return self._status

  def get_info(self):
    return {'status': self._status,
            'host': self.mqttc._host,
            'port': self.mqttc._port,
            'client_id': self.mqttc._client_id,
            'type': 'mqtt',
            'device_count': len(self._devices)}

  def on_connect(self, mqttc, obj, flags, reason_code):
    self._status = "connected"

  def on_disconnect(self, mqttc, obj, rc):
    self._status = "disconnected"

  def on_message(self, mqttc, obj, msg):
    # print('msg:', msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    # print('msg:', dir(msg))
    attr_list = ['dup', 'info', 'mid', 'payload', 'properties', 'qos', 'retain', 'state', 'timestamp', 'topic']
    # print({attr: getattr(msg, attr) for attr in attr_list if hasattr(msg, attr)})


def add_routes(app):
  print('Adding MQTT routes')

  @app.get("/api/live/connections/{connector_id}/mqtt",
           tags=["live/connections"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def get_mqtt_status(connector_id: int):
    return {"status": MqttClass.connectors_list[connector_id].get_status()}