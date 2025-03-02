from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, DATETIME
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime
from utils.auth import RoleChecker, CurrentUser, set_func_name
from sqlalchemy.ext.declarative import declared_attr
from utils.db_utils import Base
from inspect import getmembers, isdatadescriptor
from utils.db_utils import engine
from sqlalchemy import inspect


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

  # def check_struct(self):
  #   # print(self.get_structure())
  #   # print(self.__dict__)
  #   # Получаем текущие столбцы из БД
  #   # db = db_session()
  #
  #   table_name = self.__tablename__
  #   inspector = inspect(engine)
  #
  #   # Получаем текущие столбцы из БД
  #   existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
  #
  #   first_ch = True
  #   # Получаем ожидаемые столбцы из модели
  #   expected_columns = {col.name for col in self.__table__.columns}
  #   with engine.connect() as connection:
  #     for column_name in expected_columns - existing_columns:
  #       column_index = list(expected_columns).index(column_name)
  #       prev_column = list(expected_columns)[column_index - 1] if column_index > 0 else None
  #       print(f"prev_column: {prev_column} {column_index}")
  #       # Добавление нового столбца
  #       column_obj = self.__table__.columns[column_name]
  #       def_value = column_obj.default.arg
  #       if def_value and 'now' in str(def_value):
  #         def_value = 'CURRENT_TIMESTAMP'
  #       alter_stmt = ' '.join([f'ALTER TABLE {table_name} ADD COLUMN {column_name} {str(column_obj.type)}',
  #                              (f'{"" if column_obj.nullable else "NOT"} NULL ' if not def_value else ''),
  #                              f'{"" if column_obj.primary_key else ""}',
  #                              f'{"" if def_value is None else f"DEFAULT {def_value}"}',
  #                              # f'{f"AFTER {prev_column}" if prev_column else "FIRST"}'
  #                              ])
  #       connection.execute(alter_stmt)
  #       if first_ch:
  #         print(f"🔧 Изменения в структуре таблицы {table_name}:")
  #         first_ch = False
  #       print(f"✅ Добавлен столбец: {column_name} {str(column_obj.type)}")
  #
  #     for column_name in existing_columns - expected_columns:
  #       # Удаление старого столбца
  #       alter_stmt = f'ALTER TABLE {table_name} DROP COLUMN {column_name}'
  #       connection.execute(alter_stmt)
  #       if first_ch:
  #         print(f"🔧 Изменения в структуре таблицы {table_name}:")
  #         first_ch = False
  #       print(f"❌ Удалён столбец: {column_name}")

  @classmethod
  def create_routes(cls, app: FastAPI, db_session):
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
        return [
          {name: value for name, value in item.__dict__.items() if not name.startswith('_')
           } for item in items]

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
        db_item = cls(**item.model_dump(), created_by=current_user['id'], updated_by=current_user['id'])
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item

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
          raise HTTPException(status_code=404, detail=f"{cls.__tablename__} not found")
        return item

    if cls._can_update:
      params = {
        'response_model': dict,
        'tags': [cls.__tablename__],
      }
      if not (cls._can_update is True):
        params['dependencies'] = [Depends(RoleChecker(cls._can_update))]

      @app.put(f"/api/{cls.__tablename__}/{{item_id}}", **params)
      @set_func_name(f"update_{cls.__tablename__}")
      def update_item(item_id: int, item: cls.CreateSchema):
        db = db_session()
        db_item = db.query(cls).filter(cls.id == item_id).first()
        if db_item is None:
          raise HTTPException(status_code=404, detail=f"{cls.__tablename__} not found")
        for key, value in item.model_dump().items():
          setattr(db_item, key, value)
        db_item.updated_by = user['id']
        db.commit()
        db.refresh(db_item)
        return db_item

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
