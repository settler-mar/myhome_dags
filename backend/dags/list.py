from models.dag_node import DAGNode
from time import sleep
from time import time


class ListNode(DAGNode):
  name = 'list'
  version = '0.0'
  description = 'Вывод значение из списка'
  public: bool = True

  input_groups = [
    {'name': 'next', 'description': 'Следующий'},
    {'name': 'prev', 'description': 'Предыдущий'},
  ]
  params_groups = [
    {'name': 'loop',
     'description': 'Зациклить',
     'default': 1,
     'type': 'select',
     'items': {0: 'Нет', 1: 'Да'},
     'public': False
     },
    {'name': 'list',
     'description': 'Список значений',
     'type': 'list',
     'public': False
     },
    {
      'name': 'index',
      'description': 'Индекс',
      'type': 'int',
      'default': 0,
      'public': True
    }
  ]
  output_groups = [
    {'name': 'default', 'description': 'Выход'}
  ]

  sub_title = '{list}'

  def execute(self, input_keys: list):
    if 'next' in input_keys:
      self.params['index'] += 1
    if 'prev' in input_keys:
      self.params['index'] -= 1

    if self.params['index'] >= len(self.params['list']):
      if self.params['loop']:
        self.params['index'] = 0
      else:
        self.params['index'] = len(self.params['list']) - 1
        return

    if self.params['index'] < 0:
      if self.params['loop']:
        self.params['index'] = len(self.params['list']) - 1
      else:
        self.params['index'] = 0
        return

    value = self.params['list'][self.params['index']]
    if value.isdigit():
      value = int(value)
    elif value.replace('.', '', 1).isdigit():
      value = float(value)
    self.set_output(value)
