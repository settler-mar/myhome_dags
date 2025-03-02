from typing import List, Dict, Any
from models.dag_node import DAGNode
from models.root_dag import rootDag
import asyncio


class DAGTemplateBase(DAGNode, rootDag):
  """
  Класс для шаблона DAG, который может включать несколько узлов (DAGNode).
  """

  #   def execute(self):
  #     print(f"Node {self.name} started at {time()}. Delay: {self.params['delay_seconds']} seconds.")
  #     sleep(self.params['delay_seconds'])  # Асинхронная задержка
  #     print(f"Node {self.name} finished at {time()}. Delay: {self.params['delay_seconds']} seconds.")
  #     self.set_output(self.input_values.get('default', 255))

  # tpl = {'version': '0.0.3', 'name': 'New template1', 'template': {'input': [{'id': 'input_r1e2xk9lk', 'position': [165, 60], 'group': 'input', 'name': 'default', 'description': 'Input data'}], 'param': [{'id': 'param_zynrljms8', 'position': [330, 60], 'group': 'param', 'name': 'delay', 'description': 'Parameter description', 'public': True, 'params': {'type': 'int', 'default': '100', 'unit': 's'}}], 'dags': [{'id': 'kfd1vw5qt', 'position': [240, 150], 'name': 'Delay', 'params': []}]}, 'sub_title': 'Sub title1', 'updated_at': datetime.datetime(2025, 1, 2, 12, 27, 16, 619859), 'id': 3, 'description': 'Some description1', 'created_at': datetime.datetime(2025, 1, 1, 16, 31, 37, 614863)}
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
        param.update(param['params'])
        del param['params']
      self.params_groups.append(param)
    self.output_groups = template.get('output', [])

    self.dags = {}  # Список DAG-ов для выполнения
    super().__init__()

    if 'dags' in template:
      asyncio.run(self.create_from_json(template['dags']))

  @property
  def id(self):
    return f'tpl:{id(self)}'

  @property
  def code(self):
    return f'tpl:{self.name}|{self.version}'

  # async def init_dags(self):
  #   from orchestrator.dag_manager import DAGManager
  #   dag_manager = DAGManager()
  #   # for dag in self.tpl.get('template', {}).get('dags', []):
  #   #   print(f"Creating DAG {dag['name']} in template {self.name}")
  #   #   dag = await dag_manager.create_dag(name=dag['name'],
  #   #                                      params=dag['params'],
  #   #                                      position=dag['position'],
  #   #                                      root_dag=self.path)
  #   #   if dag:
  #   #     self.dags[dag.id] = dag
  #   #     if dag['position']:
  #   #       dag.set_position(*dag['position'])
  #   await dag.create_from_json(dag['outputs'])

  # def add_node(self, name: str, params: Dict[str, Any] = None, outputs: Dict[str, List[List[int]]] = None):
  #   """Добавляет узел в шаблон"""
  #   from orchestrator import DAGManager
  #   dag_manager = DAGManager()
  #   dag = dag_manager.get_dag_by_name(name, params)
  #   dag_json = dag.get_json()
  #   dag_json['outputs'] = outputs or {}
  #   self.nodes[dag.id] = dag_json
  #   del dag
  #
  # def remove_node(self, node_id: int):
  #   """Удаляет узел из шаблона"""
  #   self.nodes = [node for node in self.nodes if node['id'] != node_id]
  #   """Удаляем все связи с этим узлом"""
  #   for node in self.nodes:
  #     for output_group, output_nodes in node['outputs'].items():
  #       node['outputs'][output_group] = [(node_id, group) for node_id, group in output_nodes if node_id != node_id]
  #
  #   for group in ['inputs', 'params']:
  #     self.external_nodes_connections[group] = {group_name: [node_id, group_name]
  #                                               for group_name, [node_id, group_name]
  #                                               in self.external_nodes_connections[group].items()
  #                                               if node_id != node_id}
  #
  # def add_link(self, node_out: int, node_in: int, group_out: str = 'default', group_in: str = 'default'):
  #   """Добавляет связь между двумя узлами"""
  #   # 0 - input, -1 - params
  #   if node_in in [0, -1]:
  #     self.external_nodes_connections[['inputs', 'params'][node_in]][group_in] = [node_out, group_out]
  #     return
  #
  #   for node in self.nodes:
  #     if node['id'] == node_out:
  #       if group_out not in node['outputs']:
  #         node['outputs'][group_out] = []
  #       node['outputs'][group_out].append([node_in, group_in])
  #
  # def remove_link(self, node_out: int, node_in: int, group_out: str = 'default', group_in: str = 'default'):
  #   """Удаляет связь узла с внещним узлом"""
  #   if node_in in [0, -1]:
  #     self.external_nodes_connections[['inputs', 'params'][node_in]][group_in] = [
  #       (node_id, group) for node_id, group in self.external_nodes_connections[['inputs', 'params'][node_in]][group_in]
  #       if node_id != node_out or group != group_out
  #     ]
  #     return
  #
  #   """Удаляет связь между двумя узлами"""
  #   for node in self.nodes:
  #     if node['id'] == node_out:
  #       if group_out in node['outputs']:
  #         node['outputs'][group_out] = [(node_id, group) for node_id, group in node['outputs'][group_out]
  #                                       if node_id != node_in or group != group_in]
  #
  # def get_json(self) -> dict:
  #   """Получение метаинформации о шаблоне в формате JSON."""
  #   return {'id': self.id,
  #           'name': self.name,
  #           'params': self.params,
  #           'input_groups': self.input_groups,
  #           'params_groups': self.params_groups,
  #           'output_groups': self.output_groups,
  #           'nodes': self.nodes,
  #           'external_nodes_connections': self.external_nodes_connections,
  #           }
