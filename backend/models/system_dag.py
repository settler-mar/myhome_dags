from typing import List, Dict, Any
from models.dag_node import DAGNode


class SystemDag(DAGNode):
  version = '0.0'
  public = False

  def execute(self):
    self.set_output(self.input_values.get('default', None))


class InputDag(DAGNode):
  name = 'Input'
  description = 'Входной узел'
  points = {
    'outputs': [{'name': 'default', 'description': 'data'}],
  }


class ParamDag(DAGNode):
  name = 'Param'
  description = 'Параметр'

  points = {
    'outputs': [{'name': 'default', 'description': 'data'}],
  }


class OutputDag(DAGNode):
  name = 'Output'
  description = 'Выходной узел'

  root_tpl = None

  points = {
    'inputs': [{'name': 'default', 'description': 'data'}],
  }

  def set_root_tpl(self, root_tpl: "DAGTemplateBase"):
    self.root_tpl = root_tpl

  def process(self, input_keys: List[str]):
    self.root_tpl.updated_output = {self.name: self.input_values.get(key, None) for key in input_keys}
    print('🔗 tpl output', self.name, id(self), id(self.root_tpl), self.updated_output, self.input_values)
    self.root_tpl._run_next()
