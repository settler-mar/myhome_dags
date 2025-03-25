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
    db = db_session()
    items = db.query(DbConnections).all()
    for item in items:
      if item.type in self.connectors_class:
        module_params = {key: value for key, value in item.__dict__.items()
                         if not key.startswith('_') and
                         key not in ['created_by', 'updated_by', 'created_at', 'updated_at', 'type']}
        try:
          self.connectors[item.id] = self.connectors_class[item.type](**module_params)
        except Exception as e:
          log_print(f"Error while creating connector {item.type}")

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
      class_name = name.capitalize() + 'Class'
      module = __import__(f"{__name__}.{name}", fromlist=[class_name, 'add_routes'])
      if not hasattr(module, class_name):
        log_print(f"Class {class_name} not found in {name}")
        continue

      connect.add(name, getattr(module, class_name))
      add_routes and hasattr(module, 'add_routes') and module.add_routes(app)
  connect.init_connectors()

  if add_routes:
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
