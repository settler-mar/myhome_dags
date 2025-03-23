from dags.__pins.__base import BasePin
from time import sleep
from time import time
from utils.logs import log_print


class InputPinClass(BasePin):
  name = 'Input'
  input_groups = []

  output_groups = [
    {'name': 'default', 'description': 'Выходные данные'}
  ]

  async def set_param(self, name: str, value: any, send_update: bool = True):
    prev_value = self.params.get(name)
    await BasePin.set_param(self, name, value, send_update)
    if name == 'pin_id':
      from models.devices import Devices
      devices = Devices()
      if prev_value in devices.ports:
        devices.ports[int(prev_value)].unsubscribe(self)
      if int(value) in devices.ports:
        devices.ports[int(value)].subscribe(self)

  def income_value(self, key, new_value, prev_value):
    # key (pin.device_id, pin._id, pin.code)
    # new_value/prev_value (value, timestamp)
    data = {
      'key': key,
      'new_value': new_value,
    }
    log_print('🤖 input pin income_value', data)
    if prev_value is not None:
      data['prev_value'] = prev_value
    self.set_output(data)
    self._run_next()
