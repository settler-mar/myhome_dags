from models.dag_node import DAGNode
from time import sleep
from time import time
from utils.logs import log_print

class ListNode(DAGNode):
  name = 'filter'
  version = '0.0'
  description = 'Вывод значение из списка'
  public: bool = True
  prev_value = None
  prev_send = 0

  input_groups = [
    {'name': 'value', 'description': 'Данные'},
  ]
  params_groups = [
    {'name': 'state',
     'description': 'Режим работы',
     'default': 1,
     'type': 'select',
     'items': {0: 'Ничего не пропускать',
               1: 'Изменение значения',
               2: 'Пропускать все значения'},
     'public': True
     },
    {'name': 'time_filter',
     'description': 'Не более одного значения за период в секундах. 0 - не фильтровать',
     'type': 'int',
     'default': 0,
     'public': False
     },
  ]
  output_groups = [
    {'name': 'default', 'description': 'Выход'}
  ]

  sub_title = ''

  def execute(self, input_keys: list):
    if self.params['state'] == 0:
      log_print(id(self), self, 'state 0')
      return
    value = self.input_values.get('value', {'new_value': (0, 0)})['new_value'][0]
    if self.params['state'] == 1 and value == self.prev_value:
      log_print(id(self), self, 'state 1. NO change', value)
      return
    self.prev_value = value

    if self.params['time_filter'] > 0:
      if time() - self.prev_send < self.params['time_filter']:
        log_print(id(self), self, 'time filter', time() - self.prev_send)
        return
      self.prev_send = time()
    log_print(id(self), self, 'send', value)
    self.set_output(self.input_values.get('value', {'new_value': (0, 0)}))
