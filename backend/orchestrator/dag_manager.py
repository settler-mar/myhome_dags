from typing import List
from models.dag_node import DAGNode
import os
from models.singelton import SingletonClass
from fastapi import APIRouter, Depends
from models.root_dag import rootDag
from utils.auth import RoleChecker
import asyncio

router = APIRouter()


class DAGManager(SingletonClass):
  dags_dir: str = 'dags'
  _dags: List[DAGNode] = None

  @property
  def dags(self) -> List[DAGNode]:
    if self._dags is None:
      self._dags = self.load_dags()
    return self._dags

  def load_dags(self) -> List[DAGNode]:
    """
    Загрузка всех DAG-ов из директории.
    :return: Список объектов DAGNode.
    """
    os.makedirs(self.dags_dir, exist_ok=True)
    for file in os.listdir(self.dags_dir):
      if file.startswith('__') or file.startswith('.'):
        continue
      if file.endswith('.py'):
        print(f"Loading DAG from file: {file[:-3]}")
        __import__(f"{self.dags_dir}.{file[:-3]}", fromlist=[''])

    return [dag for dag in DAGNode.__subclasses__() if dag.public]

  def dags_json(self) -> List[dict]:
    """
    Получение списка DAG в формате JSON.
    :return: Список JSON-объектов.
    """

    def pretty_params(param):
      if isinstance(param.get('items'), dict):
        param['items'] = [{'value': key, 'title': value} for key, value in param['items'].items()]
      return param

    return [
      {'name': dag.name,
       'version': dag.version,
       'description': dag.description,
       'inputs': dag.input_groups,
       'outputs': dag.output_groups,
       'params': list(map(pretty_params, dag.params_groups or [])),
       'sub_title': dag.sub_title,
       } for dag in self.dags
    ]

  def get_dag_by_name(self, name: str, params: dict = None, is_source_class=False, path=None) -> DAGNode:
    """
    Получение DAG по имени.
    :param name: Имя DAG.
    :param params: Параметры.
    :return: Объект DAGNode.
    """

    if name.startswith('tpl:'):
      from orchestrator.template_manager import TemplateManager
      name, version = name[4:].split('|')
      return TemplateManager().get_template(name=name, version=version, params=params, path=path)

    if name.startswith('pin:'):
      from models.devices import PinsManager
      return PinsManager().get_pin(name[4:], params)

    for dag_base in self.dags:
      if dag_base.name == name:
        if is_source_class:
          return dag_base

        dag = dag_base()
        if params:
          for key, value in params.items():
            asyncio.run(dag.set_param(key, value, False))
        return dag

  async def create_dag(self, name: str,
                       params: dict = None,
                       position: List[int] = None,
                       root_dag: rootDag = None) -> DAGNode:
    """
    Создание нового DAG.
    :param name: Имя DAG.
    :param params: Параметры.
    """

    dag = self.get_dag_by_name(name, params, rootDag.path)
    if not dag:
      print(f"DAG {name} not found")
      return

    if position:
      dag.position = position

    if not root_dag:
      from orchestrator.orchestrator import Orchestrator
      root_dag = Orchestrator()
    await root_dag.add_dag(dag)

    return dag


# Api routes
@router.get("/list/dags", tags=["dags"], dependencies=[Depends(RoleChecker('admin'))])
async def get_available_dags():
  """
  Get available DAGs to create
  """
  return DAGManager().dags_json()


@router.get("/list/pins", tags=["dags"], dependencies=[Depends(RoleChecker('admin'))])
async def get_available_dags_pins():
  """
  Get available DAGs to create pins
  """
  from models.devices import PinsManager
  return PinsManager().dags_pins_json()
