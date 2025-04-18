from typing import Union

from future.builtins import isinstance
from models.singelton import SingletonClass
from fastapi import Depends, APIRouter, Query
from models.root_dag import rootDag
from utils.socket_utils import connection_manager
from pydantic import BaseModel, Field
from utils.auth import RoleChecker
import json
import os
import asyncio
import threading
from utils.logs import log_print

router = APIRouter()


class Orchestrator(SingletonClass, rootDag):
  """
  Оркестратор для управления выполнением DAG-ов.
  Отвечает за асинхронное выполнение, управление состоянием и взаимодействие между узлами.
  """

  def __init__(self):
    if self.is_initialized:
      return
    self.is_initialized = True
    super().__init__()
    self.load_dags()

  def load_dags(self):
    from models.devices import Devices
    if Devices().ports is None:
      threading.Timer(1, self.load_dags).start()
      return

    log_print('Orchestrator loaded from file')

    def load_dags_from_file(file_name: str):
      try:
        if os.path.exists(f'../store/{file_name}'):
          with open(f'../store/{file_name}', 'r') as f:
            return json.loads(f.read())
      except Exception as e:
        log_print(f"Error loading DAGs from file {file_name}: {e}")
      return None

    dags_data = load_dags_from_file('orchestrator.json') or load_dags_from_file('orchestrator_bk.json')
    if dags_data:
      asyncio.create_task(self.create_from_json(dags_data))
      with open('../store/orchestrator_bk.json', 'w') as f:
        f.write(json.dumps(dags_data))
    else:
      log_print("No DAGs found in file, creating empty DAGs")


@router.get("/orchestrator/save", tags=["dags"], dependencies=[Depends(RoleChecker('admin'))])
async def save_dags():
  """
  Save all DAGs to file
  """
  with open('../store/orchestrator.json', 'w') as f:
    f.write(json.dumps(Orchestrator().list_dags(is_clean=True, load_all=True)))
  return {'status_code': 200}


@router.get("/orchestrator", tags=["dags"], dependencies=[Depends(RoleChecker('admin'))])
async def get_json():
  """
  Get all DAGs as JSON
  """
  return Orchestrator().list_dags(load_all=True)


@router.get("/dags", tags=["dags"], dependencies=[Depends(RoleChecker('admin'))])
async def get_dags(is_simple: bool = False):
  """
  Get all active DAGs
  """
  return Orchestrator().list_dags(is_simple=is_simple)


class postDag(BaseModel):
  dag_name: str = Field('Delay', description='DAG name from /dag_list', example='Delay'),
  position_x: int = Field(100, description='X position', example=100),
  position_y: int = Field(100, description='Y position', example=100)
  page: str = Query('main', description='Page name', example='main')


class putDag(BaseModel):
  params: dict = Field({}, description='DAG params', example={'delay_seconds': 10}),


@router.post("/dags/add", tags=["dags"], dependencies=[Depends(RoleChecker('admin'))])
async def add_dag(dag_item: postDag, tpl_id: str = None):
  """
  Add DAG to orchestrator
  """
  from orchestrator.dag_manager import DAGManager
  dag_manager = DAGManager()
  root_dag = None
  if dag_item.page.startswith('vtpl:'):
    tpl_id = dag_item.page[1:]
    from orchestrator.template_manager import TemplateManager
    root_dag = TemplateManager.templates.get(tpl_id)
    if root_dag is None:
      return {"error": f"Template {tpl_id} not found"}, 422
  dag = await dag_manager.create_dag(dag_item.dag_name,
                                     position=[dag_item.position_x, dag_item.position_y],
                                     root_dag=root_dag)
  if dag is None:
    return {"error": f"DAG {dag_item.dag_name} not found"}, 422
  if dag_item.page:
    dag.setPage(dag_item.page)
  return dag.get_json()


@router.put("/dags/{dag_id}", tags=["dags"], dependencies=[Depends(RoleChecker('admin'))])
async def update_dag(dag_id: Union[int, str], dag_item: putDag):
  """
  Update DAG params
  """
  if isinstance(dag_id, str) and dag_id.isdigit():
    dag_id = int(dag_id)
  if dag_id not in Orchestrator().dags:
    return {"error": f"DAG {dag_id} not found"}, 422
  dag = Orchestrator().dags[dag_id]
  for key, value in dag_item.params.items():
    if key == 'position':
      dag.set_position(*value)
      continue
    if key in dag.params:
      dag.set_params(key, value)
    dag.send_update()
  return dag.get_json()


@router.delete("/templates_dag/{tpl_id}/{dag_id}", tags=["dags_templates"],
               dependencies=[Depends(RoleChecker('admin'))])
@router.delete("/dags/{dag_id}", tags=["dags"], dependencies=[Depends(RoleChecker('admin'))])
async def remove_dag(dag_id: Union[int, str], tpl_id: Union[int, str] = None):
  """
  Remove DAG from orchestrator
  """
  if isinstance(dag_id, str) and dag_id.isdigit():
    dag_id = int(dag_id)
  if tpl_id is not None:
    from orchestrator.template_manager import TemplateManager
    root_dag = TemplateManager.templates.get(tpl_id)
    if root_dag is None:
      return {"error": f"Template {tpl_id} not found"}, 422
  else:
    root_dag = Orchestrator()
  if root_dag.remove_dag(dag_id):
    data = {"type": "dag", "action": "remove", "data": {"id": dag_id}}
    if tpl_id:
      data['tpl_id'] = f'tpl:{tpl_id}'
    await connection_manager.broadcast(data)
    return {'status_code': 204}
  return {"error": f"DAG {dag_id} not found"}, 422


class postConnection(BaseModel):
  from_id: Union[int, str] = Field(0, description='DAG output id from /dags or 0 for global output', example=0),
  from_port: str = Field('default', description='Output group name', example='default'),
  to_id: Union[int, str] = Field(0, description='DAG input id from /dags or 0 for input, -1 for params', example=0),
  to_type: str = Field('in', description='Input group name', example='in'),
  to_port: str = Field('default', description='Input group name', example='default')
  page: str = Query(None, description='Page name', example='main')


class paramsDag(BaseModel):
  params: dict = Field({}, description='DAG params', example={'delay_seconds': 10}),


@router.post("/dags/{dag_id}/params", tags=["dags"], dependencies=[Depends(RoleChecker('admin'))])
@router.post("/templates/{tpl_id}/{dag_id}/params", tags=["dags_templates"],
             dependencies=[Depends(RoleChecker('admin'))])
async def params_dag(dag_id: Union[int, str], dag_item: paramsDag, tpl_id: Union[int, str] = None):
  """
  Update DAG params
  """
  if isinstance(dag_id, str) and dag_id.isdigit():
    dag_id = int(dag_id)
  dags = Orchestrator().dags

  if tpl_id:
    from orchestrator.template_manager import TemplateManager
    if not tpl_id.startswith('tpl:') or not tpl_id in TemplateManager.templates:
      return {"error": f"Template {tpl_id} not found"}, 422
    dags = TemplateManager.templates[tpl_id].dags

  if dag_id not in dags:
    return {"error": f"DAG {dag_id} not found"}, 422
  dag = dags[dag_id]
  await dag.set_params(dag_item.params)
  return dag.params


@router.post("/dags/connections", tags=["dags"], dependencies=[Depends(RoleChecker('admin'))])
async def add_connection(connection: postConnection):
  """
  Add connection between two DAGs
  """
  root = Orchestrator()
  if connection.page.startswith('vtpl:'):
    from orchestrator.template_manager import TemplateManager
    tpl_id = connection.page[1:]
    root = TemplateManager.templates.get(tpl_id)
    if root is None:
      return {"error": f"Template {tpl_id} not found"}, 422

  if await root.add_dag_connections(connection.from_id,
                                    connection.to_id,
                                    connection.to_type,
                                    connection.from_port,
                                    connection.to_port):
    return {'code': 'ok'}, 204
  return {"error": f"Connection not found"}, 422


@router.delete("/templates/connections/{from_id}/{from_port}/{to_type}/{to_id}/{to_port}/{tpl_id}",
               tags=["dags_templates"],
               dependencies=[Depends(RoleChecker('admin'))])
@router.delete("/dags/connections/{from_id}/{from_port}/{to_type}/{to_id}/{to_port}",
               tags=["dags"],
               dependencies=[Depends(RoleChecker('admin'))])
async def remove_connection(from_id: Union[int, str], from_port: str, to_id: Union[int, str], to_type: str,
                            to_port: str, tpl_id: Union[int, str] = None):
  """
  Remove connection between two DAGs
  """
  if tpl_id is not None:
    from orchestrator.template_manager import TemplateManager
    root_dag = TemplateManager.templates.get(f'tpl:{tpl_id}')
    if root_dag is None:
      return {"error": f"Template {tpl_id} not found"}, 422
  else:
    root_dag = Orchestrator()
  if root_dag.remove_dag_connections(dag_out=from_id, dag_in=to_id, group_out=from_port, group_in=to_port,
                                     to_type=to_type):
    return {'code': 'ok'}, 204
  return {"error": f"Connection not found"}, 422
