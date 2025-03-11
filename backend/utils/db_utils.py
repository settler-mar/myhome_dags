from glob import escape

from sqlalchemy import create_engine, insert
from sqlalchemy.orm import declarative_base, sessionmaker
import importlib
import pkgutil
import os
from fastapi import FastAPI
from utils.configs import config
from sqlalchemy import inspect
from sqlalchemy.schema import CreateTable

connect_args = {}
if config['db'].get('check_same_thread') is not None:
  connect_args['check_same_thread'] = config['db']['check_same_thread']

engine = create_engine(config['db']['url'],
                       echo=config['db']['echo'], echo_pool=config['db']['echo_pool'],
                       connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def escape_val(type_name, val):
  if type_name in ['VARCHAR', 'TEXT', 'CHAR']:
    return f"'{val}'"
  return val


def update_struct_sqlite(table_name, expected_columns, existing_columns, inspector):
  create_query = str(CreateTable(Base.metadata.tables[table_name]).compile(dialect=engine.dialect))
  rename_old_table_query = f"ALTER TABLE {table_name} RENAME TO {table_name}_backup"
  # столбцы которые есть в БД, и в модели по имени
  columns_in_both = [col for col in existing_columns if col[0] in [el[0] for el in expected_columns]]
  insert_query = f"""INSERT INTO {table_name} ({', '.join([col[0] for col in columns_in_both])})
                            SELECT {', '.join([col[0] for col in columns_in_both])} FROM {table_name}_backup"""

  create_query = create_query.split('\n')
  expected_columns = {el[0]: el[1:] for el in expected_columns if el[2] is not None}

  for i, line in enumerate(create_query):
    line = line.rstrip()
    column_name = line.strip().split(' ')[0]
    if (column_name in expected_columns and
        str(expected_columns[column_name][1]) not in line):
      is_last_line = True
      if line.endswith(','):
        is_last_line = False
        line = line[:-1]
      create_query[i] = f'{line} DEFAULT {escape_val(*expected_columns[column_name])},'
      if is_last_line:
        create_query[i] = create_query[i] + ','
  create_query = '\n'.join(create_query)

  with engine.connect() as connection:
    if inspector.has_table(f"{table_name}_backup"):
      connection.execute(f"DROP TABLE {table_name}_backup")
    connection.execute(rename_old_table_query)
    connection.execute(create_query)
    connection.execute(insert_query)
    connection.execute(f"DROP TABLE {table_name}_backup")


def update_struct_default(table_name, expected_columns, existing_columns, inspector):
  pass


def check_structure():
  def filter_type(type_name):
    return str(type_name).split('(')[0]

  def get_default_value(default, type_name=''):
    if default is None:
      return None
    if hasattr(default, 'arg'):
      default = default.arg
    if type_name in ['VARCHAR', 'TEXT', 'CHAR']:
      return f"'{default}'".replace("''", "'")
    if '.now' in str(default) or '.utcnow' in str(default):
      return 'CURRENT_TIMESTAMP'
    return str(default)

  update_struct_function = {
    'sqlite': update_struct_sqlite,
  }.get(config['db']['url'].split(':')[0].split('+')[0], lambda: update_struct_default)

  inspector = inspect(engine)
  for table_name in Base.metadata.tables:
    # Получаем текущие столбцы из БД
    existing_columns = {(col['name'], filter_type(col['type']), col['default'])
                        for col in inspector.get_columns(table_name)}
    existing_columns = {(col[0], col[1], get_default_value(col[2], col[1])) for col in existing_columns}

    # Получаем ожидаемые столбцы из модели
    expected_columns = {(col.name, filter_type(col.type), get_default_value(col.default))
                        for col in Base.metadata.tables[table_name].columns}
    expected_columns = {(col[0], col[1], get_default_value(col[2], col[1])) for col in expected_columns}
    session = SessionLocal()

    # Сравниваем
    if existing_columns != expected_columns:
      print(f"🔧 Изменения в структуре таблицы {table_name}")
      update_struct_function(table_name, expected_columns, existing_columns, inspector)


def init_db(app: FastAPI):
  for file in os.listdir('db_models'):
    if file.startswith('__') or file.startswith('.'):
      continue
    if file.endswith('.py'):
      print(f"Loading DB MODEL from file: {file[:-3]}")
      importlib.import_module(f"db_models.{file[:-3]}")

  Base.metadata.create_all(bind=engine)

  from models.base_db_model import BaseModelDB
  for cls in BaseModelDB.__subclasses__():
    cls.create_routes(app, db_session)

  check_structure()


# Зависимость для получения сессии
def db_session():
  session = SessionLocal()
  try:
    return session
  finally:
    session.close()
