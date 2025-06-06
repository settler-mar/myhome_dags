from models.singelton import SingletonClass
from os import path
import os

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime
from utils.auth import RoleChecker, CurrentUser, set_func_name
from sqlalchemy.ext.declarative import declared_attr
from utils.db_utils import Base
from inspect import getmembers, isdatadescriptor
from utils.db_utils import Base, db_session
from db_models.connections import Connections as DbConnections
from utils.logs import log_print


class Connectors(SingletonClass):
  """
  Класс для хранения коннекторов и их параметров
  """
  app = None
  connectors_class: dict = None
  connectors: dict = None

  def __init__(self):
    if self.is_initialized:
      return
    self.is_initialized = True

    self.connectors_class = {}
    self.connectors = {}

  def add(self, name, connector_class):
    self.connectors_class[name] = connector_class

  def init_connectors(self):
    print('Connectors class initialized from DB')
    with db_session() as db:
      items = db.query(DbConnections).all()
      for item in items:
        if item.type in self.connectors_class:
          module_params = {key: value for key, value in item.__dict__.items()
                           if not key.startswith('_') and
                           key not in ['created_by', 'updated_by', 'created_at', 'updated_at', 'type']}
          try:
            self.connectors[item.id] = self.connectors_class[item.type](**module_params)
            print(f"Connector {item.type} ({item.id}) created with params: {module_params}")
          except Exception as e:
            log_print(f"Error while creating connector {item.type}")
        else:
          log_print(f"Connector {item.type} not found in connectors_class")

  def start_connectors(self):
    for connector in self.connectors.values():
      try:
        hasattr(connector, 'start') and connector.start()
      except Exception as e:
        log_print(f"Error while starting connector {connector._id}")


def init_connectors(app, add_routes: bool = True):
  connect = Connectors()

  log_print(f"Connectors class initialized:")
  connectors_dir = path.join(path.dirname(__file__))
  os.makedirs(connectors_dir, exist_ok=True)
  for file in os.listdir(connectors_dir):
    if file.startswith('_') or file.startswith('.'):
      continue
    if file.endswith('.py'):
      log_print(f"Loading connector from file: {file[:-3]}")
      name = file[:-3]
      class_name = ''.join([n.capitalize() for n in name.split('_')]) + 'Class'
      module = __import__(f"{__name__}.{name}", fromlist=[class_name, 'add_routes'])
      if not hasattr(module, class_name):
        log_print(f"Class {class_name} not found in {name}")
        continue

      connect.add(name, getattr(module, class_name))
      add_routes and hasattr(module, 'add_routes') and module.add_routes(app)
  connect.init_connectors()

  if add_routes:
    @app.get("/api/connections_list",
             tags=["connections"],
             response_model=list,
             dependencies=[Depends(RoleChecker('admin'))])
    def get_connections_list():
      return [
        {
          'code': name,
          'name': connector.name if hasattr(connector, 'name') else connector.__name__,
          'type': connector.type,
          'params': connector.params if hasattr(connector, 'params') else {},
          'devices_params': connector.devices_params if hasattr(connector, 'devices_params') else {},
          'description': connector.description if hasattr(connector, 'description') else None,
          'icon': connector.icon if hasattr(connector, 'icon') else None,
          'rules': connector.rules if hasattr(connector, 'rules') else None,
          'actions': connector.actions if hasattr(connector, 'actions') else None,
        }
        for name, connector in connect.connectors_class.items()
      ]

    @app.get("/api/live/connections",
             tags=["live/connections"],
             response_model=dict,
             dependencies=[Depends(RoleChecker('admin'))])
    def get_connections_list():
      return {name: connector.get_info() for name, connector in connect.connectors.items()}

    @app.get("/api/live/connections/status",
             tags=["live/connections"],
             response_model=dict,
             dependencies=[Depends(RoleChecker('admin'))])
    def get_connections_status():
      log_print(connect.connectors)
      return {name: connector.get_status() for name, connector in connect.connectors.items() if
              hasattr(connector, 'get_status')}

  return connect
