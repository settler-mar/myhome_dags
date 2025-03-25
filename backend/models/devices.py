from models.singelton import SingletonClass
import os

from fastapi import FastAPI, Depends, HTTPException
from datetime import datetime
from utils.auth import RoleChecker, CurrentUser, set_func_name
from utils.db_utils import Base
from utils.db_utils import Base, db_session
from db_models.connections import Connections as DbConnections
from db_models.devices import Devices as DbDevices
from db_models.ports import Ports as DbPorts
from models.connections import Connectors
from typing import Union, List
from models.dag_node import DAGNode
import asyncio
from utils.socket_utils import connection_manager


class Port:
  def __init__(self, _device, **kwargs):
    self._id = kwargs['id']
    self.code = kwargs['code']
    self.label = kwargs['label']
    self.access = kwargs['access']
    self.type = kwargs['type']
    self.values_variant = kwargs['values_variant']
    self.description = kwargs['description']
    self.name = kwargs['name']
    self.mode = kwargs['mode']
    self.unit = kwargs['unit']
    self.device_id = kwargs['device_id']  # device_id

    self.device = _device
    self.value = None
    self.value_raw = None
    self.last_update: datetime = None
    self.last_send: datetime = None
    self.subscriber = []

    if self.type == 'numeric':
      # set len of values_variant to 4 (min, max, step, didgits) (add None if not exist)
      if self.values_variant:
        self.values_variant += [None] * (4 - len(self.values_variant))

  def info(self):
    return {
      'id': self._id,
      'code': self.code,
      'label': self.label,
      'access': self.access,
      'type': self.type,
      'values_variant': self.values_variant,
      'description': self.description,
      'name': self.name,
      'mode': self.mode,
      'unit': self.unit,
      'device_id': self.device_id,
      'value': self.value,
      'value_raw': self.value_raw,
      'last_update': self.last_update,
      'last_send': self.last_send,
      'subscriber_count': len(self.subscriber),
    }

  def get_value(self):
    return self.value

  def _value_to_raw(self, value):
    if self.type == 'numeric':
      value = float(value)
      if self.values_variant:
        if self.values_variant[2] is not None:  # step
          value = round(value / self.values_variant[2]) * self.values_variant[2]
        if self.values_variant[0] is not None:  # min
          value = max(value, self.values_variant[0])
        if self.values_variant[1] is not None:  # max
          value = min(value, self.values_variant[1])
        if self.values_variant[3] is not None:  # didgits
          value = round(value, self.values_variant[3])
        else:
          value = round(value, 4)
      return value, value
    if self.type == 'binary' and self.values_variant:
      value = int(value)
      return value, self.values_variant[value > 0]
    return value, value

  def set_value(self, value):  # set new value and send to device
    value, raw_value = self._value_to_raw(value)
    self.value = value
    self.last_send = datetime.now()
    self.device.send_value(self, raw_value)
    connection_manager.broadcast_log(level='value',
                                     message=f'🤖 set port({self.code}) value',
                                     permission='admin',
                                     direction='out',
                                     device_id=self.device_id,
                                     pin_id=self._id,
                                     pin_name=self.name,
                                     value=value,
                                     value_raw=raw_value)

  def _raw_to_value(self, value_raw):
    if self.type == 'numeric':
      return value_raw
    if self.type == 'binary' and self.values_variant:
      value = [0, 255][self.values_variant.index(value_raw)]
      if value and self.value:
        return self.value
      return value
    return value_raw

  def income_value(self, value_raw):  # set new value from device and send to port
    prev_value = (self.value, self.last_update.timestamp()) if self.value else None
    self.last_update = datetime.now()
    self.value_raw = value_raw
    value = self._raw_to_value(value_raw)
    self.value = value

    connection_manager.broadcast_log(level='value',
                                     message=f'income_value {self.code}',
                                     permission='admin',
                                     direction='in',
                                     device_id=self.device_id,
                                     pin_id=self._id,
                                     pin_name=self.name,
                                     value=value,
                                     value_raw=value_raw)

    for subscriber in self.subscriber:
      if hasattr(subscriber, 'income_value'):
        subscriber.income_value((self.device_id, self._id, self.code), (value, self.last_update.timestamp()),
                                prev_value)
      else:
        print('skip subscriber', subscriber)

  def subscribe(self, subscriber):
    self.subscriber.append(subscriber)

  def unsubscribe(self, subscriber):
    self.subscriber = [item for item in self.subscriber if id(item) != id(subscriber)]


class Device:
  def __init__(self, app, connector, params):
    self.app = app
    self.connector = connector
    self.params = params['params']
    self.id = params['id']
    self.code = params['code']
    self.name = params['name']
    self.type = params['type']
    self.model = params['model']
    self.vendor = params['vendor']
    self.description = params['description']
    self.connection_id = params['connection_id']
    self.location_id = params['location_id']
    self.connector.add_device(self)
    self.ports = {}
    self.port_codes = {}
    self.prev_state = None

  def set_value(self, port_id, value):
    port_id = int(self.port_codes.get(port_id, port_id))
    if port_id in self.ports:
      self.ports[port_id].set_value(value)

  def get_value(self, port_id):
    port_id = int(self.port_codes.get(port_id, port_id))
    if port_id in self.ports:
      return self.ports[port_id].get_value()

  def income_value(self, port_id, value):
    port_id = self.port_codes.get(port_id, port_id)
    if isinstance(port_id, str):
      if port_id.isdigit():
        port_id = int(port_id)
      else:
        return  # port not found
    if port_id in self.ports:
      self.ports[port_id].income_value(value)

  def send_value(self, port, value):
    self.connector.send_value(self, port, value)

  def add_port(self, port):
    self.ports[port['id']] = Port(**port, _device=self)
    self.port_codes[port['code']] = port['id']
    return self.ports[port['id']]

  def get_info(self):
    return {
      'id': self.id,
      'code': self.code,
      'name': self.name,
      'type': self.type,
      'model': self.model,
      'vendor': self.vendor,
      'description': self.description,
      'connection_id': self.connection_id,
      'location_id': self.location_id,
      'params': self.params,
      'port_count': len(self.ports),
      'port_codes': {port.code: port.info() for port in self.ports.values()},
    }


class Devices(SingletonClass):
  """
  Класс для хранения устройств и их параметров
  """
  app = None
  devices_class: dict = None
  devices: dict = None
  devices_names: dict = None
  ports: dict = None

  def __init__(self):
    if self.is_initialized:
      return
    self.is_initialized = True

    self.devices_class = {}
    self.devices = {}
    self.devices_names = {}
    self.ports = {}
    print(f"Devices class initialized:")
    self.init_device()

  def add_port(self, port):
    if not isinstance(port, dict):
      port = port.__dict__
    port = {key: value for key, value in port.items() if not key.startswith('_')}
    self.ports[port['id']] = self.devices[port['device_id']].add_port(port)

  def add_device(self, item):
    self.devices[item.id] = Device(self.app,
                                   Connectors().connectors[item.connection_id],
                                   {key: value for key, value in item.__dict__.items()
                                    if not key.startswith('_')})
    self.devices_names[item.name] = item.id
    if hasattr(self.devices[item.id], 'add_device'):
      Connectors().connectors[item.connection_id].add_device(self.devices[item.id])

  def init_device(self):
    self.devices = {}
    db = db_session()
    items = db.query(DbDevices).all()
    connectors = Connectors().connectors
    for item in items:
      if item.connection_id in connectors:
        self.add_device(Device(self.app, connectors[item.connection_id], item.__dict__))
      else:
        print(f"Device {item.name}({item.id}) not found in devices_class or connection_id not found in Connectors")

    ports = db.query(DbPorts).all()
    for port in ports:
      if port.device_id in self.devices:
        self.add_port(port)
      else:
        print(f"Port {port.id} not found in devices[{port.device_id}]")


def devices_init(app, add_routes: bool = True):
  devices = Devices()

  if add_routes:
    @app.get("/api/live/devices",
             tags=["live/devices"],
             response_model=dict,
             dependencies=[Depends(RoleChecker('admin'))])
    def get_connections_list():
      return {name: item.get_info() for name, item in devices.items()}

    @app.post("/api/live/dag/{dag_id}/{port_name}/set",
              tags=["live/dags"],
              dependencies=[Depends(RoleChecker('admin'))])
    @app.post("/api/live/dag/{tpl_id}/{dag_id}/{port_name}/set",
              tags=["live/dags"],
              dependencies=[Depends(RoleChecker('admin'))])
    def set_port_value(port_name: str,
                       dag_id: Union[str, int],
                       value: Union[str, int],
                       tpl_id: str = None):
      if tpl_id is not None:
        from orchestrator.template_manager import TemplateManager
        tpl_id = tpl_id[4:]
        if tpl_id not in TemplateManager.templates:
          return {"status": 'error', "message": 'Template not found'}
        root = TemplateManager.templates[tpl_id]
      else:
        from orchestrator.orchestrator import Orchestrator
        root = Orchestrator()
      if isinstance(dag_id, str) and dag_id.isdigit():
        dag_id = int(dag_id)
      if dag_id in root.dags:
        root.dags[dag_id].set_value(port_name, value, 'from web')
        return {"status": 'ok'}
      return {"status": 'error', "message": 'DAG not found'}, 422

    @app.get("/api/live/connections/{device_id}/{port_id}/get",
             tags=["live/connections"],
             dependencies=[Depends(RoleChecker('admin'))])
    def get_port_value(device_id: Union[str, int], port_id: Union[str, int]):
      device_id = int(devices.devices_names.get(device_id, device_id))
      if device_id in devices.devices:
        return {"status": 'ok', "value": devices.devices[device_id].get_value(port_id)}
      return {"status": 'error', "message": 'Device or port not found'}


class PinsManager(SingletonClass):
  pins_class: dict = None
  pins_dir: str = 'dags/__pins'

  def __init__(self):
    if self.is_initialized:
      return
    self.is_initialized = True
    self.pins_class = self.load_pins_class()

  def load_pins_class(self):
    pins_map = {}
    os.makedirs(self.pins_dir, exist_ok=True)
    for file in os.listdir(self.pins_dir):
      if file.startswith('__') or file.startswith('.'):
        continue
      if file.endswith('.py'):
        print(f"Loading PINS DAG from file: {file[:-3]}")
        name = file[:-3]
        class_name = name.capitalize() + 'PinClass'
        module = __import__(f"{self.pins_dir.replace('/', '.')}.{name}", fromlist=[class_name])
        pins_map[name] = getattr(module, class_name)
        pins_map[name].code = 'pin:' + file[:-3]
    return pins_map

  def dags_pins_json(self) -> List[dict]:
    """
    Получение списка DAG в формате JSON которые могут быть использованы в качестве пинов.
    :return: Список JSON-объектов.
    """
    # pins_class
    return [
      {'name': dag.name,
       'code': code,
       'version': dag.version,
       'description': dag.description,
       'inputs': dag.input_groups,
       'outputs': dag.output_groups,
       'params': dag.params_groups,
       'sub_title': dag.sub_title,
       } for code, dag in self.pins_class.items()
    ]

  def get_pin(self, code, params):
    if code in self.pins_class:
      dag = self.pins_class[code]()
      if params:
        for key, value in params.items():
          asyncio.create_task(dag.set_param(key, value, send_update=False))
      return dag
    return None
