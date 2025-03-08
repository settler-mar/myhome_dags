from typing import List, Dict, Any
from models.dag_node import DAGNode
from models.root_dag import rootDag
import asyncio


class DAGTemplateBase(DAGNode, rootDag):
  """
  Класс для шаблона DAG, который может включать несколько узлов (DAGNode).
  """

  def __init__(self, tpl: dict = None, path: List[str] = None):
    self.path = [*(path or [])]
    self.name = tpl.get('name', 'Template')
    self.version = tpl.get('version', '0.0.1')
    if (self.name, self.version) in self.path:
      raise ValueError(f'Loop in DAG template path: {self.path}')
    self.path.append((self.name, self.version))

    self.description = tpl.get('description', 'Template description')
    self.sub_title = tpl.get('sub_title', 'Template sub title')
    template = tpl.get('template', {})

    self.input_groups = template.get('input', [])
    self.params_groups = []
    for param in template.get('param', []):
      if 'params' in param:
        for key, value in param['params'].items():
          if key in ['min', 'max', 'step']:
            param['params'][key] = float(value)
        param.update(param['params'])
        del param['params']
      self.params_groups.append(param)
    self.output_groups = template.get('output', [])

    self.dags = {}  # Список DAG-ов для выполнения
    super().__init__()

    if 'dags' in template:
      dag_id_map = asyncio.run(self.create_from_json(template['dags']))

    for input_group in [self.input_groups, self.params_groups, self.output_groups]:
      for input_dag in input_group:
        input_dag['outputs'] = input_dag.get('outputs', {}).get('default', [])
        for index, output in enumerate(input_dag['outputs']):
          if output[1] in dag_id_map:
            input_dag['outputs'][index] = (output[0], dag_id_map[output[1]], output[2])

    for output_dags in self.output_groups:
      output_dags['pin'].set_root_tpl(self)

  @property
  def id(self):
    return f'tpl:{id(self)}'

  @property
  def code(self):
    return f'tpl:{self.name}|{self.version}'

  async def set_param(self, param_name: str, value: any, send_update: bool = True):
    await DAGNode.set_param(self, param_name, value, send_update)
    value = self.params.get(param_name)
    print('🤓 dag set param', param_name, value)
    for param in self.params_groups:
      if param['name'] == param_name:
        for output in param['outputs']:
          if output[0] in ['in']:
            output[1].set_input(value, output[2])
          elif output[0] in ['param']:
            await output[1].set_param(output[2], value)
        continue

  def execute(self, input_keys: List[str]):
    print('🤖 dag execute')
    execute_dags = {}
    for input_dag in self.input_groups:
      if input_dag['name'] in input_keys:
        for output in input_dag['outputs']:
          if output[0] in ['in']:
            output[1].set_input(self.input_values.get(input_dag['name']), output[2])
            if output[1] not in execute_dags:
              execute_dags[output[1]] = []
            if output[2] not in execute_dags[output[1]]:
              execute_dags[output[1]].append(output[2])
          if output[0] in ['param']:
            output[1].set_param(output[2], self.input_values.get(input_dag['name']))

    for dag, input_keys in execute_dags.items():
      dag.process(input_keys)
