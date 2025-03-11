import json
from sqlalchemy import TypeDecorator, types


class Json(TypeDecorator):
  @property
  def python_type(self):
    return object

  impl = types.String(2048)

  def process_bind_param(self, value, dialect):
    return json.dumps(value)

  def process_literal_param(self, value, dialect):
    return value

  def process_result_value(self, value, dialect):
    try:
      return json.loads(value)
    except (TypeError, ValueError):
      return None
