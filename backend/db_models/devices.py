from models.base_db_model import BaseModelDB
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from pydantic import BaseModel
from sqlalchemy import TypeDecorator, types
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from utils.auth import pwd_context, RoleChecker, CurrentUser
from sqlalchemy.orm import sessionmaker, Session
from db_models.common.json import Json
from sqlalchemy.ext.declarative import declared_attr


class Devices(BaseModelDB):
  __tablename__ = "devices"

  _can_view = 'root'
  _can_create = 'root'
  _can_read = 'admin'
  _can_update = 'root'
  _can_get_structure = 'admin'

  id = Column(Integer, primary_key=True, index=True)
  code = Column(String, unique=True, index=True)
  name = Column(String, unique=True, index=True)
  model = Column(String)
  vendor = Column(String)
  description = Column(String)
  type = Column(String)
  params = Column(Json)

  @declared_attr
  def connection_id(cls):
    return Column(Integer, ForeignKey('connections.id'))

  @declared_attr
  def location_id(cls):
    return Column(Integer, ForeignKey('locations.id'))

  class CreateSchema(BaseModel):
    name: str
    description: str
    type: str
    params: dict
    connection_id: int
    location_id: int
