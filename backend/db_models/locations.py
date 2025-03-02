from models.base_db_model import BaseModelDB
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, DateTime
from pydantic import BaseModel
from sqlalchemy import TypeDecorator, types
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from utils.auth import pwd_context, RoleChecker, CurrentUser
from sqlalchemy.orm import sessionmaker, Session
from db_models.common.json import Json


class Locations(BaseModelDB):
  __tablename__ = "locations"

  _can_view = 'root'
  _can_create = 'root'
  _can_read = 'admin'
  _can_update = 'root'
  _can_get_structure = 'admin'

  id = Column(Integer, primary_key=True, index=True)
  name = Column(String, unique=True, index=True)
  color = Column(String)
  description = Column(String)
  icon = Column(String)

  class CreateSchema(BaseModel):
    name: str
    color: str
    description: str
    icon: str
