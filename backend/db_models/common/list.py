import json
from sqlalchemy import TypeDecorator, types


class List(TypeDecorator):
  @property
  def python_type(self):
    return object

  impl = types.String(1024)

  def process_bind_param(self, value, dialect):
    if isinstance(value, list):
      return json.dumps(value)
    return None

  def process_literal_param(self, value, dialect):
    return value

  def process_result_value(self, value, dialect):
    try:
      values = json.loads(value)
      if isinstance(values, list):
        return values
      return None
    except (TypeError, ValueError):
      return None
