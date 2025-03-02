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
  description = 'Парамет'


class OutputDag(DAGNode):
  name = 'Output'
  description = 'Выходной узел'
