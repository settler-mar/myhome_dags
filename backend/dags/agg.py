from models.dag_node import DAGNode
from time import sleep
from time import time
from utils.logs import log_print


class AggNode(DAGNode):
  name = 'agg'
  version = '0.0'
  description = 'Агрегация данных'
  public: bool = True
  values = None
  max_count = 100

  input_groups = [
    {'name': 'default', 'description': 'Значение'},
  ]
  params_groups = [
    {'name': 'mode',
     'description': 'Режим агрегации',
     'default': 'agg',
     'type': 'select',
     'items': ['agg', 'max', 'min', 'sum', 'avg'],
     'public': False
     },
    {'name': 'ttl',
     'description': 'Время жизни данных в секундах',
     'default': 120,
     'type': 'int',
     'public': False
     },
    {
      'name': 'channel',
      'description': 'Обработка данных',
      'type': 'select',
      'default': 0,
      'items': {0: 'Игнорировать источник', 1: 'Для каждого источника 1 значение'},
      'public': False
    }
  ]
  output_groups = [
    {'name': 'default', 'description': 'Выход'}
  ]

  sub_title = ''

  def execute(self, input_keys: list):
    key = self.input_values['default']['key']
    value, ts = self.input_values['default']['new_value']
    try:
      if isinstance(value, str):
        value = float(value)

      if self.params['channel'] == 1:
        if self.values is None:
          self.values = {}
        elif self.params['ttl'] > 0:
          for k, v in self.values.items():
            if time() - v[1] > self.params['ttl']:
              del self.values[k]
        self.values[key] = (value, ts)
        values = self.values.items()
      else:
        if self.values is None:
          self.values = []
        elif self.params['ttl'] > 0:
          while len(self.values) > 0 and time() - self.values[0][1] > self.params['ttl']:
            self.values.pop(0)
        self.values.append((value, ts))
        if len(self.values) > self.max_count:
          self.values.pop(0)
        values = self.values

      if self.params['mode'] == 'agg':
        value = sum([v[0] for v in values]) / len(values)
      elif self.params['mode'] == 'max':
        value = max([v[0] for v in values])
      elif self.params['mode'] == 'min':
        value = min([v[0] for v in values])
      elif self.params['mode'] == 'sum':
        value = sum([v[0] for v in values])
      elif self.params['mode'] == 'avg':
        value = sum([v[0] for v in values]) / len(values)
      self.set_output(value)
    except Exception as e:
      log_print(f"Error: {e}")
