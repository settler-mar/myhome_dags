from models.base_db_model import BaseModelDB
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, DateTime
from pydantic import BaseModel
from sqlalchemy import TypeDecorator, types
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from utils.auth import pwd_context, RoleChecker, CurrentUser
from sqlalchemy.orm import sessionmaker, Session
from db_models.common.json import Json


class Connections(BaseModelDB):
  __tablename__ = "connections"

  _can_view = 'root'
  _can_create = 'root'
  _can_read = 'admin'
  _can_update = 'root'
  _can_get_structure = 'admin'

  id = Column(Integer, primary_key=True, index=True)
  name = Column(String(100), unique=True, index=True)
  type = Column(String(50))
  host = Column(String(100))
  port = Column(Integer)
  username = Column(String(30))
  password = Column(String(50))
  params = Column(Json)

  class CreateSchema(BaseModel):
    name: str
    host: str
    type: str
    password: str
    params: dict
