from sqlalchemy import TypeDecorator, types
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, DateTime

from utils.auth import pwd_context, RoleChecker, CurrentUser


class PasswordHash(TypeDecorator):
  impl = String

  def process_bind_param(self, value, dialect):
    if value:
      return pwd_context.hash(value)
    return None

  def process_result_value(self, value, dialect):
    return value
