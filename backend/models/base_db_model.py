from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, DATETIME
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from datetime import datetime
from utils.auth import RoleChecker, CurrentUser, set_func_name
from sqlalchemy.ext.declarative import declared_attr
from utils.db_utils import Base
from inspect import getmembers, isdatadescriptor
from utils.db_utils import engine
from sqlalchemy import inspect
from utils.logs import log_print
from pydantic import create_model, BaseModel, Field
from typing import Optional, get_origin
import sqlalchemy as sa
from sqlalchemy.ext.mutable import MutableDict


class BaseModelDB(Base):
  __abstract__ = True

  @declared_attr
  def created_at(cls):
    return Column(DateTime, default=datetime.now)

  @declared_attr
  def created_by(cls):
    return Column(Integer, ForeignKey('users.id'))

  @declared_attr
  def updated_at(cls):
    return Column(DateTime, default=datetime.now)

  @declared_attr
  def updated_by(cls):
    return Column(Integer, ForeignKey('users.id'))

  column_element = {
    'created_by': {
      'type': 'alias',
      'table': 'users',
      'template': '{name} ({id})',
      'key': 'id'
    },
    'updated_by': {
      'type': 'alias',
      'table': 'users',
      'template': '{name} ({id})',
      'key': 'id',
    }
  }
  readonly_columns = ['id']

  _can_view = True  # list of records
  _can_create = True
  _can_read = True  # one record
  _can_update = 'admin'
  _can_get_structure = True
  _can_drop = 'root'

  @classmethod
  def generate_create_schema(cls):
    if hasattr(cls, 'CreateSchema'):
      return

    fields = {}

    def get_example(py_type, column_name):
      if py_type is str:
        return {
          'color': '#FFFFFF',
        }.get(column_name, "example")
      if py_type is int:
        return 1
      if py_type is float:
        return 1.0
      if py_type is bool:
        return True
      if py_type is dict:
        return {"key": "value"}
      return None

    for column in cls.__table__.columns:
      if column.name in {'id', 'created_by', 'created_at', 'updated_by', 'updated_at'}:
        continue

      # Определение python-типа
      try:
        py_type = column.type.python_type
      except NotImplementedError:
        if isinstance(column.type, (sa.JSON, MutableDict)):
          py_type = dict
        else:
          py_type = str

      is_optional = (
          column.nullable
          or column.default is not None
          or column.server_default is not None
      )

      typ = Optional[py_type] if is_optional else py_type
      default_value = None if is_optional else ...

      if column.default is not None:
        try:
          val = column.default.arg
          default_value = val() if callable(val) else val
        except Exception:
          pass

      # Пример и описание
      field_info = Field(
        default=default_value,
        title=column.name.replace('_', ' ').capitalize(),
        description=str(column.type),
        example=get_example(py_type, column.name)
      )

      fields[column.name] = (typ, field_info)

    model_name = f"{cls.__name__}CreateSchema"
    cls.CreateSchema = create_model(model_name, __base__=BaseModel, **fields)

  @classmethod
  def get_structure(cls):
    # print('get_structure')
    parent_class = cls.__bases__[0]
    parents_struct = []
    class_struct = []
    for column in cls.__table__.columns:
      item = {
        'name': column.name,
        "type": str(column.type),
        "nullable": column.nullable,
        "primary_key": column.primary_key
      }
      if hasattr(parent_class, item['name']):
        if item['name'] in parent_class.column_element:
          item['element'] = parent_class.column_element[item['name']]
        item['readonly'] = True
        parents_struct.append(item)
      else:
        if item['name'] in cls.column_element:
          item['element'] = cls.column_element[item['name']]
        item['readonly'] = item['name'] in cls.readonly_columns
        class_struct.append(item)
    columns = class_struct + parents_struct
    return columns

  def to_dict(self):
    return {
      key: value
      for key, value in self.__dict__.items()
      if not key.startswith('_')
    }

  @classmethod
  def create_routes(cls, app: FastAPI, db_session):
    cls.generate_create_schema()

    if hasattr(cls, 'custom_routes'):
      cls.custom_routes(app, db_session)

    if cls._can_view:
      params = {
        'response_model': list,
        'tags': [cls.__tablename__],
      }
      if not (cls._can_view is True):
        params['dependencies'] = [Depends(RoleChecker(cls._can_view))]

      @app.get(f"/api/{cls.__tablename__}/", **params)
      @set_func_name(f"list_of_{cls.__tablename__}")
      def list_items():
        db = db_session()
        items = db.query(cls).all()
        return [item.to_dict() for item in items]

    if cls._can_create:
      params = {
        'response_model': dict,
        'tags': [cls.__tablename__],
      }
      if not (cls._can_create is True):
        params['dependencies'] = [(Depends(RoleChecker(cls._can_create)))]

      @app.post(f"/api/{cls.__tablename__}/", **params)
      @set_func_name(f"create_{cls.__tablename__}")
      def create_item(item: cls.CreateSchema, current_user: CurrentUser):
        db = db_session()
        db_item = cls(**item.model_dump(), created_by=current_user.id, updated_by=current_user.id)
        db.add(db_item)
        try:
          db.commit()
        except Exception as e:
          db.rollback()
          raise HTTPException(status_code=400, detail=f"Error creating {cls.__tablename__}: {e}")
        db.refresh(db_item)
        log_print(f"Created {cls.__tablename__} with id {db_item.id}")
        return db_item.to_dict()

    if cls._can_read:
      params = {
        'response_model': dict,
        'tags': [cls.__tablename__],
      }
      if not (cls._can_read is True):
        params['dependencies'] = [Depends(RoleChecker(cls._can_read))]

      @app.get(f"/api/{cls.__tablename__}/{{item_id}}", **params)
      @set_func_name(f"read_one_{cls.__tablename__}")
      def read_item(item_id: int):
        db = db_session()
        item = db.query(cls).filter(cls.id == item_id).first()
        if item is None:
          log_print(f"Item {cls.__tablename__} with id {item_id} not found")
          raise HTTPException(status_code=404, detail=f"{cls.__tablename__} not found")
        return item.to_dict()

    if cls._can_update:
      params = {
        'response_model': dict,
        'tags': [cls.__tablename__],
      }
      if not (cls._can_update is True):
        params['dependencies'] = [Depends(RoleChecker(cls._can_update))]

      @app.put(f"/api/{cls.__tablename__}/{{item_id}}", **params)
      @set_func_name(f"update_{cls.__tablename__}")
      def update_item(item_id: int, item: cls.CreateSchema, current_user: CurrentUser):
        db = db_session()
        db_item = db.query(cls).filter(cls.id == item_id).first()
        if db_item is None:
          raise HTTPException(status_code=404, detail=f"{cls.__tablename__} not found")
        for key, value in item.model_dump().items():
          setattr(db_item, key, value)
        db_item.updated_by = current_user.id
        db.commit()
        db.refresh(db_item)
        log_print(f"update {cls.__tablename__} with id {item_id} by {current_user.id}")
        return db_item.to_dict()

    if cls._can_drop:
      params = {
        'response_model': dict,
        'tags': [cls.__tablename__],
      }
      if not (cls._can_drop is True):
        params['dependencies'] = [Depends(RoleChecker(cls._can_drop))]

      @app.delete(f"/api/{cls.__tablename__}/{{item_id}}", **params)
      @set_func_name(f"drop_{cls.__tablename__}")
      def drop_item(item_id: int):
        db = db_session()
        db_item = db.query(cls).filter(cls.id == item_id).first()
        if db_item is None:
          raise HTTPException(status_code=404, detail=f"{cls.__tablename__} not found")
        db.delete(db_item)
        db.commit()
        return {'status': 'ok'}

    if cls._can_get_structure:
      params = {
        'response_model': list,
        'tags': [cls.__tablename__, 'structure'],
      }
      if not (cls._can_get_structure is True):
        params['dependencies'] = [Depends(RoleChecker(cls._can_get_structure))]

      @app.get(f"/api/structure/{cls.__tablename__}", **params)
      @set_func_name(f"get_structure_for_class_{cls.__tablename__}")
      def get_structure():
        return cls.get_structure()

    params = {
      'response_model': dict,
      'tags': [cls.__tablename__, 'permissions'],
      'dependencies': [Depends(RoleChecker('admin'))]
    }

    @app.get(f"/api/permissions/{cls.__tablename__}", **params)
    @set_func_name(f"get_permissions_for_class_{cls.__tablename__}")
    def get_permissions():
      return {
        'view': cls._can_view,
        'create': cls._can_create,
        'read': cls._can_read,
        'update': cls._can_update,
        'drop': cls._can_drop,
        'get_structure': cls._can_get_structure
      }

    params['dependencies'] = [Depends(RoleChecker())]

    @app.get(f"/api/permissions/{cls.__tablename__}/my", **params)
    @set_func_name(f"get_my_permissions_for_class_{cls.__tablename__}")
    def get_my_permissions(current_user: CurrentUser):
      permissions = {
        'view': cls._can_view,
        'create': cls._can_create,
        'read': cls._can_read,
        'update': cls._can_update,
        'drop': cls._can_drop,
        'get_structure': cls._can_get_structure
      }
      return {
        key: RoleChecker(permissions[key], is_test=True)(current_user) for key in permissions
      }
