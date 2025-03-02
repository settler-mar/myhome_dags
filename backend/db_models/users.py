from models.base_db_model import BaseModelDB
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, DateTime
from pydantic import BaseModel
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from utils.auth import pwd_context, RoleChecker, CurrentUser
from sqlalchemy.orm import sessionmaker, Session
from db_models.common.password import PasswordHash


class User(BaseModelDB):
  __tablename__ = "users"

  _can_view = 'root'
  _can_create = 'root'
  _can_read = 'admin'
  _can_update = 'root'
  _can_get_structure = 'admin'

  id = Column(Integer, primary_key=True, index=True)
  username = Column(String, unique=True, index=True)
  password = Column(PasswordHash)
  full_name = Column(String)
  email = Column(String, unique=True, index=True)
  is_active = Column(Boolean, default=True)
  role = Column(String, default='user')
  tg_id = Column(Integer, unique=True, index=True)
  otp = Column(String)
  last_login = Column(DateTime, default=datetime.utcnow)
  login_count = Column(Integer, default=0)

  class CreateSchema(BaseModel):
    username: str
    password: str
    full_name: str
    email: str
    role: str = 'user'
    tg_id: int
    otp: str = None


  def set_last_login(self):
    self.last_login = datetime.utcnow()
    self.login_count += 1

  @classmethod
  def custom_routes(cls, app: FastAPI, db_session):
    # get count users. if 0 - create admin user
    db = db_session()
    count_users = db.query(User).count()
    if count_users == 0:
      admin = User(username='admin', password='admin', role='root', created_by=0, updated_by=0)
      db.add(admin)
      db.commit()

    class NewPassword(BaseModel):
      password: str
      password_repeat: str
      old_password: str

    @app.post(f"/api/me", tags=['auth'], response_model=dict, dependencies=[(Depends(RoleChecker('user')))])
    def set_password(set_password: NewPassword,
                     current_user: CurrentUser):
      db = db_session()
      user = db.query(User).filter(User.id == current_user.id).first()
      if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
      if not pwd_context.verify(set_password.old_password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect old password")
      if set_password.password != set_password.password_repeat:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")
      user.password = set_password.password
      db.commit()
      print('set password')
      return {'status': 'ok'}
