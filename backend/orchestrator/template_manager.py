import os.path
from typing import List
from models.singelton import SingletonClass
from db_models.templates import Template
from utils.db_utils import db_session
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from utils.socket_utils import connection_manager
from datetime import datetime
from models.dag_template import DAGTemplateBase
from utils.auth import RoleChecker
import asyncio
from orchestrator.orchestrator import postDag

router = APIRouter()


class TemplateManager(SingletonClass):
  templates = {}

  def get_templates(self) -> List[Template]:
    with db_session() as db:
      return db.query(Template).all()

  def get_template(self, name: str, version: str, params: dict = None, path: List[str] = None) -> DAGTemplateBase:
    with db_session() as db:
      tpl = (db
             .query(Template)
             .filter(Template.name == name)
             .filter(Template.version == version)
             .first())
    if not tpl:
      return
    dag = DAGTemplateBase(tpl=tpl.__dict__, path=path, params=params)
    dag.root_name = f'v{dag.id}'
    return dag


def save_to_file(template):
  file_path = os.path.realpath(os.path.join(__file__, '..', '..', 'templates', 'export'))
  if not os.path.exists(file_path):
    os.makedirs(file_path)

  file_name = f"{template['name']}_{template['version']}.json"
  file_name = file_name.lower().replace(' ', '_').replace('-', '_')
  file_name = ''.join([c for c in file_name if c.isalnum() or c in ['_', '.']])

  # save template as JSON. Columns: name,template,version,description,sub_title
  print(f"Saving template to {os.path.join(file_path, file_name)}")
  with open(os.path.join(file_path, file_name), 'w') as f:
    template = {k: v for k, v in template.items() if k in ['name', 'template', 'version', 'description', 'sub_title']}
    f.write(str(template))


@router.get("/templates", tags=["dags_templates"], dependencies=[Depends(RoleChecker('admin'))])
def get_templates():
  return TemplateManager().get_templates()


class DAGTemplate(BaseModel):
  name: str = Field(default='DAGTemplate', title='Название шаблона', description='Название шаблона')
  template: dict = Field(default={}, title='Шаблон', description='Шаблон')
  version: str = Field(default='0.0.1', title='Версия шаблона', description='Версия шаблона')
  description: str = Field(default='', title='Описание', description='Описание')
  sub_title: str = Field(default='', title='Подзаголовок', description='Подзаголовок')
  template: dict = Field(default={}, title='Шаблон', description='Шаблон')


@router.post("/templates", tags=["dags_templates"], dependencies=[Depends(RoleChecker('admin'))])
async def create_template(template: DAGTemplate, db: Session = Depends(db_session)):
  if not template.name or template.name == 'New template':
    return {'code': 'error', 'message': 'Invalid template name'}
  db_tpl = db.query(Template).filter(Template.name == template.name).filter(
    Template.version == template.version).first()
  if db_tpl:
    return {'code': 'error', 'message': 'Template already exists'}
  db.add(Template(**template.__dict__))
  db.commit()
  template = db.query(Template).filter(Template.name == template.name).order_by(Template.id.desc()).first().__dict__
  data = {k: v for k, v in template.items() if k != '_sa_instance_state'}
  save_to_file(template)
  await connection_manager.broadcast({"type": "template",
                                      "action": "add",
                                      "data": data})
  return {'code': 'ok'}


class DAGTemplateUpdate(BaseModel):
  name: str = Field(default='DAGTemplate', title='Название шаблона', description='Название шаблона')
  version: str = Field(default='0.0.1', title='Версия шаблона', description='Версия шаблона')
  template: dict = Field(default={}, title='Шаблон', description='Шаблон')
  sub_title: str = Field(default='', title='Подзаголовок', description='Подзаголовок')
  description: str = Field(default='', title='Описание', description='Описание')


@router.post("/templates/save", tags=["dags_templates"], dependencies=[Depends(RoleChecker('admin'))])
async def save_template(data: DAGTemplateUpdate):
  with db_session() as db:
    db_tpl = (db
              .query(Template)
              .filter(Template.name == data.name)
              .filter(Template.version == data.version)
              .first())
    if not db_tpl:
      return {'code': 'error', 'message': 'Template not found'}
    db_tpl.description = data.description
    db_tpl.sub_title = data.sub_title
    db_tpl.template = data.template
    db_tpl.updated_at = datetime.now()
    db.commit()
    template = (db
                .query(Template)
                .filter(Template.name == data.name)
                .filter(Template.version == data.version)
                ).first().__dict__
    data = {k: v for k, v in template.items() if k != '_sa_instance_state'}
    save_to_file(template)
    await connection_manager.broadcast({"type": "template",
                                        "action": "update",
                                        "data": data})
  return {'code': 'ok'}


@router.get("/templates/active_list", tags=["dags_templates"], dependencies=[Depends(RoleChecker('admin'))])
async def get_active_templates():
  return {k: {'name': v.name, 'version': v.version} for k, v in TemplateManager.templates.items()}


@router.get("/templates/get/{tpl_id}", tags=["dags_templates"], dependencies=[Depends(RoleChecker('admin'))])
async def get_active_template(tpl_id: str):
  tpl = TemplateManager.templates.get(tpl_id)
  if not tpl:
    return {'code': 'error', 'message': 'Init template not found'}, 422
  return TemplateManager.templates.get(tpl_id).list_dags(is_clean=False, load_all=True)
