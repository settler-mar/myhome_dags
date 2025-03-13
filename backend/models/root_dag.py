from traceback import print_tb

from models.dag_node import DAGNode
from utils.socket_utils import connection_manager
from models.system_dag import InputDag, ParamDag, OutputDag
from typing import Union


class rootDag:
  path: list = None
  dags: dict = None

  async def add_dag(self, dag: DAGNode) -> int:
    """Добавляет DAG для выполнения"""
    dag_id = dag.id
    if self.dags is None:
      self.dags = {}
    self.dags[dag_id] = dag
    if self.path:
      print(f"{self.id}: {len(self.dags)}. Added DAG {dag.name} with id {dag_id}")
    else:
      print(f"{len(self.dags)}. Added DAG {dag.name} with id {dag_id}")
    if not self.path:
      await connection_manager.broadcast({"type": "dag", "action": "add", "data": dag.get_json()})
    return dag_id

  def kill(self):
    """Останавливает выполнение всех DAG-ов"""
    for dag in self.dags.values():
      dag.kill()

  def list_dags(self, is_clean: bool = False, load_all: bool = False, is_simple: bool = False):
    """Возвращает список всех DAG-ов с метаинформацией"""

    def prettify(dag):
      # if isinstance(dag["id"], str) and dag["id"].split(':')[0] in ['pin', 'tpl']:
      #   dag["name"] = dag["id"].split(':')[0] + ':' + dag["name"]
      if is_clean:
        return {key: dag[key] for key in
                ['code', 'params', 'position', 'page', 'outputs', 'id', 'version', 'is_simple']}
      return dag

    items = self.dags or {}
    if not load_all:
      items = {key: dag for key, dag in items.items() if dag.is_simple == is_simple}
    return [
      prettify(dag.get_json()) for _, dag in items.items()
    ]

  async def create_from_json(self, dag_json: list):
    """Создает DAG из JSON-объекта"""
    from orchestrator.dag_manager import DAGManager
    dag_manager = DAGManager()
    dag_id_map = {}
    for dag_params in dag_json:
      dag = await dag_manager.create_dag(name=dag_params.get('code', dag_params.get('name')),
                                         params=dag_params['params'],
                                         position=dag_params['position'],
                                         root_dag=self)
      if dag is None:
        continue
      dag.setPage(dag_params.get('page', 'main'))
      dag.is_simple = dag_params.get('is_simple', False)
      dag_id_map[dag_params['id']] = dag

    if self.path:
      print(f'{self.id}: add_gloabal_ports')
      pins_map = [
        (getattr(self, 'input_groups', []), InputDag),
        (getattr(self, 'params_groups', []), ParamDag),
        (getattr(self, 'output_groups', []), OutputDag),
      ]
      for pins, dag_type in pins_map:
        for pin in pins:
          dag = dag_type()
          dag.set_position(*pin['position'])
          await self.add_dag(dag)
          pin['pin'] = dag
          dag_id_map[pin['id']] = dag
          if 'name' in pin:
            dag.name = pin['name']

    for dag_params in dag_json:
      if dag_params['id'] not in dag_id_map:
        print(f"Error: DAG {dag_params['id']} not found")
        continue
      dag = dag_id_map[dag_params['id']]
      for group_out, output_nodes in dag_params['outputs'].items():
        for in_type, dag_in, group_in in output_nodes:
          if not dag_in in dag_id_map:
            print(f"Error: DAG {dag_in} not found")
          else:
            await dag.add_output(dag_id_map[dag_in], in_type, group_out, group_in, send_update=False)
    return dag_id_map

  def remove_dag(self, dag_id: int):
    """Удаляет DAG по идентификатору"""
    if self.dags is None:
      self.dags = {}

    if dag_id in self.dags:
      for dag in self.dags.values():
        dag.remove_output(self.dags[dag_id], all_groups=True, send_update=False)
      del self.dags[dag_id]
      return True
    return False

  async def add_dag_connections(self,
                                dag_out: Union[int, str],
                                dag_in: Union[int, str],
                                in_type: str = 'in',
                                group_out: str = 'default',
                                group_in: str = 'default'):
    """Добавляет связь между двумя DAG-ами"""
    if isinstance(dag_out, str) and dag_out.isnumeric():
      dag_out = int(dag_out)
    if isinstance(dag_in, str) and dag_in.isnumeric():
      dag_in = int(dag_in)
    print('add_dag_connections', [dag_out, dag_in])
    print(self.dags.keys())
    if dag_out in self.dags and dag_in in self.dags:
      print('add_dag_connections start')
      dag = self.dags[dag_out]
      await dag.add_output(self.dags[dag_in], in_type, group_out, group_in)
      return True
    return

  def remove_dag_connections(self, dag_out: int, dag_in: int, group_out: str = 'default', group_in: str = 'default',
                             to_type: str = 'in'):
    """Удаляет связь между двумя DAG-ами"""
    if dag_out in self.dags and dag_in in self.dags:
      dag = self.dags[dag_out]
      dag.remove_output(self.dags[dag_in], group_out, group_in, to_type)
      return True
    return False
