from sqlalchemy import Column, Integer, String, DateTime, JSON
from utils.db_utils import Base
from datetime import datetime
from db_models.common.json import Json

class Template(Base):
  __tablename__ = "templates"

  id = Column(Integer, primary_key=True, index=True)
  name = Column(String, nullable=False)
  template = Column(Json)
  version = Column(String)
  description = Column(String)
  sub_title = Column(String)
  created_at = Column(DateTime, default=datetime.utcnow)
  updated_at = Column(DateTime, default=datetime.utcnow)
