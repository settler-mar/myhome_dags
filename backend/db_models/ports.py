from models.base_db_model import BaseModelDB
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, DateTime
from pydantic import BaseModel
from sqlalchemy import TypeDecorator, types
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from utils.auth import pwd_context, RoleChecker, CurrentUser
from sqlalchemy.orm import sessionmaker, Session
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

  id = Column(Integer, primary_key=True, index=True)
  code = Column(String)
  name = Column(String, unique=True, index=True)
  label = Column(String)
  description = Column(String)
  access = Column(Integer)
  mode = Column(String)
  type = Column(String)
  unit = Column(String)
  values_variant = Column(List)

  @declared_attr
  def device_id(cls):
    return Column(Integer, ForeignKey('devices.id'))

  class CreateSchema(BaseModel):
    name: str
    description: str
    type: str
    device_id: int
