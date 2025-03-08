from models.dag_node import DAGNode
from time import sleep
from time import time


class ConditionNode(DAGNode):
  name = 'Condition'
  version = '0.0'
  description = 'Условный оператор'
  public: bool = True

  input_groups = [
    {'name': 'value', 'description': 'Значение'},
  ]
  params_groups = [
    {'name': 'condition',
     'description': 'Условие',
     'type': 'select',
     'default': '==',
     'items': ['==', '!=', '>', '>=', '<', '<='],
     'public': False},
    {'name': 'threshold',
     'description': 'Порог',
     'type': 'float',
     'default': 0,
     'public': True},
    {'name': 'out_value',
     'description': 'Выводимое значение в порт true/false',
     'type': 'select',
     'default': -1,
     'items': {-1: 'input(value)', 0: 'false (0)', 255: 'true (255)', 127: 'half/mode (127)', -2: 'custom'},
     'public': False,
     }, {
      'name': 'custom_value',
      'description': 'Пользовательское значение',
      'type': 'str',
      'public': True,
    }
  ]
  output_groups = [
    {'name': 'default', 'description': 'Выходные данные по умолчанию'},
    {'name': 'false', 'description': 'Выходные данные при ложном условии'},
    {'name': 'true', 'description': 'Выходные данные при истинном условии'},
  ]

  sub_title = '{condition} {threshold}'

  def execute(self, input_keys: list):
    value = float(self.input_values.get('value', {'new_value': (0, 0)})['new_value'][0])
    threshold = self.params['threshold']
    condition = self.params['condition']

    result = {
      '==': value == threshold,
      '!=': value != threshold,
      '>': value > threshold,
      '>=': value >= threshold,
      '<': value < threshold,
      '<=': value <= threshold,
    }[condition]

    value = self.params.get('out_value', -1)
    if value == -1:
      value = self.input_values.get('value')
    elif value == -2:
      value = self.params.get('custom_value')
    self.set_output(255 if result else 0)
    self.set_output(value, 'true' if result else 'false')
