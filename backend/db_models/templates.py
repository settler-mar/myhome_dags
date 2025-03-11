from sqlalchemy import Column, Integer, String, DateTime, JSON
from utils.db_utils import Base
from datetime import datetime
from db_models.common.json import Json

class Template(Base):
  __tablename__ = "templates"

  id = Column(Integer, primary_key=True, index=True)
  name = Column(String(55), nullable=False)
  template = Column(Json)
  version = Column(String(20))
  description = Column(String(255))
  sub_title = Column(String(100))
  created_at = Column(DateTime, default=datetime.utcnow)
  updated_at = Column(DateTime, default=datetime.utcnow)
