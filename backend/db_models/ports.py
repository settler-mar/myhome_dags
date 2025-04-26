from models.base_db_model import BaseModelDB
from pydantic_core.core_schema import nullable_schema
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, DateTime
from pydantic import BaseModel
from sqlalchemy import TypeDecorator, types
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from utils.auth import pwd_context, RoleChecker, CurrentUser
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.mutable import MutableDict
from db_models.common.json import Json
from db_models.common.list import List
from sqlalchemy.ext.declarative import declared_attr


class Ports(BaseModelDB):
  __tablename__ = "ports"

  _can_view = 'root'
  _can_create = 'root'
  _can_read = 'admin'
  _can_update = 'root'
  _can_get_structure = 'admin'

  id = Column(Integer, primary_key=True, index=True, autoincrement=True)
  code = Column(String(100))
  name = Column(String(100), index=True, nullable=False)
  label = Column(String(100))
  description = Column(String(255))
  access = Column(Integer)
  mode = Column(String(20))
  type = Column(String(20))
  unit = Column(String(20))
  groups_name = Column(String(100))
  values_variant = Column(List)

  @declared_attr
  def device_id(cls):
    return Column(Integer, ForeignKey('devices.id'), nullable=False)

  @declared_attr
  def metadata_id(cls):
    return Column(Integer, ForeignKey('port_metadata.id'), nullable=True)
