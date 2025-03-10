from dags.__pins.__base import BasePin
from time import sleep
from time import time


class OutputPinClass(BasePin):
  name = 'Output'

  input_groups = [
    {'name': 'default', 'description': 'Выходные данные'}
  ]

  output_groups = []

  def execute(self, input_keys: list):
    from models.devices import Devices
    devices = Devices()

    pin_id = int(self.params['pin_id'])
    if not devices.ports or pin_id not in devices.ports:
      print('🤖 output pin is not output', pin_id)
      return
    value = self.input_values.get('default', {}).get('new_value', (0, 0))[0]
    devices.ports[pin_id].set_value(value)
