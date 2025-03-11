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

router = APIRouter()


class TemplateManager(SingletonClass):
  def __init__(self):
    self.db = db_session()

  def get_templates(self) -> List[Template]:
    return db_session().query(Template).all()

  def get_template(self, name: str, version: str, params: dict = None, path: List[str] = None) -> DAGTemplateBase:
    tpl = (db_session()
           .query(Template)
           .filter(Template.name == name)
           .filter(Template.version == version)
           .first())
    if not tpl:
      return
    dag = DAGTemplateBase(tpl=tpl.__dict__, path=path)

    if params:
      print('init template with params', params)
      asyncio.create_task(dag.set_params(params, False))
      # for key, value in params.items():
      #   dag.set_param(key, value, False)
    return dag


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
  db = db_session()
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
  await connection_manager.broadcast({"type": "template",
                                      "action": "update",
                                      "data": data})
  return {'code': 'ok'}
