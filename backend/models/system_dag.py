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


class ParamDag(DAGNode):
  name = 'Param'
  description = 'Параметр'


class OutputDag(DAGNode):
  name = 'Output'
  description = 'Выходной узел'

  root_tpl = None

  def set_root_tpl(self, root_tpl: "DAGTemplateBase"):
    self.root_tpl = root_tpl

  def process(self, input_keys: List[str]):
    self.root_tpl.updated_output = {key: self.input_values.get(key, None) for key in input_keys}
    print('🔗 tpl output', id(self.root_tpl), self.root_tpl, self.updated_output, self.input_values)
    self.root_tpl._run_next()
