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
import re

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


def extract_columns_block(query):
  match = re.search(r'\((.*)\)\s*(ENGINE|CHARSET|COLLATE|$)', query, re.DOTALL)
  return match.group(1) if match else ""


def parse_columns(columns_block):
  lines = [line.strip().rstrip(',') for line in columns_block.splitlines()]
  columns = []
  for line in lines:
    if line.upper().startswith(('PRIMARY', 'UNIQUE', 'KEY', 'CONSTRAINT', 'INDEX', 'FOREIGN')):
      continue
    match = re.match(
      r'`?(\w+)`?\s+(\w+)(?:\((\d+)\))?(.*?)$',
      line,
      re.IGNORECASE
    )
    if match:
      name, col_type, size, rest = match.groups()
      full_type = f"{col_type.upper()}({size})" if size else col_type.upper()
      default_match = re.search(r'DEFAULT\s+([^\s,]+)', rest, re.IGNORECASE)
      nullable = "NOT NULL" not in rest.upper()
      default = default_match.group(1).strip("'\"") if default_match else None
      auto_inc = "AUTO_INCREMENT" in rest.upper()
      columns.append((name, full_type, default, nullable, auto_inc))
  return columns


# --- Парсим типы и AUTO_INCREMENT ---
def parse_type_info(query):
  pattern = r'`?(\w+)`?\s+([A-Z]+)(\(\d+\))?(.*?)(?:,|\n|\))'
  matches = re.findall(pattern, query, flags=re.IGNORECASE | re.DOTALL)
  result = {}
  for name, typ, size, rest in matches:
    full_type = f"{typ.upper()}{size}" if size else typ.upper()
    auto_inc = "AUTO_INCREMENT" in rest.upper()
    nullable = "NOT NULL" not in rest.upper()
    result[name] = (full_type, auto_inc, nullable)
  return result


def normalize_type(typ: str) -> str:
  typ = typ.upper()

  # Упростим тип и размер отдельно
  base_match = re.match(r'^(\w+)(?:\((\d+)\))?', typ)
  if not base_match:
    return typ

  base, size = base_match.groups()

  # Маппинг MySQL-синонимов
  mapping = {
    'INTEGER': 'INT',
    'DEC': 'DECIMAL',
    'BOOL': 'BOOLEAN',
    'TINYTEXT': 'TEXT',
    'MEDIUMTEXT': 'TEXT',
    'LONGTEXT': 'TEXT',
    'TINYINT': 'BOOLEAN' if size == '1' else 'TINYINT'
  }

  normalized_base = mapping.get(base, base)
  # Вернуть с размером, если он релевантен
  if normalized_base in {'BOOLEAN', 'TEXT', 'INT', 'DECIMAL'}:
    return normalized_base
  return f"{normalized_base}({size})" if size else normalized_base


def update_struct_mysql(table_name, expected_columns, existing_columns, inspector):
  if table_name in ['users']:
    # игнорируем изменения в этих таблицах
    return
  expected_columns = list(expected_columns)
  create_query = str(CreateTable(Base.metadata.tables[table_name]).compile(dialect=engine.dialect))
  # SHOW CREATE TABLE table_name
  with engine.connect() as connection:
    cur = connection.execute(f"SHOW CREATE TABLE {table_name}")
    current_query = cur.fetchone()[1]

  columns_block = extract_columns_block(current_query)
  current_columns = parse_columns(columns_block)

  expected_by_name = {col[0]: col for col in expected_columns}
  current_by_name = {col[0]: col for col in current_columns}

  existing_names = [col[0] for col in current_columns]
  final_columns = existing_names.copy()

  type_overrides = parse_type_info(create_query)
  # Обновим expected_columns с длинами из create_query
  expected_columns = [
    (
      name,
      type_overrides.get(name, (typ, False))[0],  # тип
      default,
      False if auto_inc else type_overrides.get(name, (typ, False))[2],  # AUTO_INCREMENT требует NOT NULL
      type_overrides.get(name, (typ, False))[1]  # auto_increment
    )
    for name, typ, default, nullable, auto_inc in expected_columns
  ]

  with engine.connect() as connection:
    def execute(stmt):
      print(stmt)
      connection.execute(f"ALTER TABLE {table_name} {stmt};")

    # --- Генерация ALTER запросов ---
    for name, exp_type, exp_default, exp_nullable, exp_auto_inc in expected_columns:
      is_text = exp_type.startswith("TEXT")

      # нормализация DEFAULT TRUE/FALSE → 1/0 для BOOL
      normalized_default = exp_default
      if exp_type.upper().startswith("BOOL") or exp_type.upper().startswith("BOOLEAN"):
        if isinstance(exp_default, str):
          if exp_default.strip().lower() == "true":
            normalized_default = "1"
          elif exp_default.strip().lower() == "false":
            normalized_default = "0"

      nullability = "NULL" if exp_nullable else "NOT NULL"
      default_clause = f"DEFAULT {normalized_default}" if normalized_default and not is_text else ""
      auto_clause = "AUTO_INCREMENT" if exp_auto_inc else ""

      parts = [
        f"{'ADD' if name not in current_by_name else 'MODIFY'} COLUMN {name}",
        exp_type,
        nullability,
        default_clause,
        auto_clause
      ]
      stmt = " ".join(p for p in parts if p).strip()

      # сравнение, только если колонка уже есть
      if name not in current_by_name:
        execute(stmt)
      else:
        _, cur_type, cur_default, cur_nullable, cur_auto_inc = current_by_name[name]
        cur_default = {
          'NULL': None,
          'CURRENT_TIMESTAMP': 'CURRENT_TIMESTAMP',
          'CURRENT_DATE': 'CURRENT_DATE'
        }.get(cur_default, cur_default)
        if (normalize_type(cur_type) != normalize_type(exp_type)
            or cur_default != normalized_default
            or cur_nullable != exp_nullable
            or cur_auto_inc != exp_auto_inc):
          # print(f'    default   {cur_default} > {normalized_default}')
          # print(f'    nullable  {cur_nullable} > {exp_nullable}')
          # print(f'    type      {cur_type} > {exp_type}')
          # print(f'    auto_inc  {cur_auto_inc} > {exp_auto_inc}')
          # print('    ---' * 5)
          execute(stmt)

    # Удаление лишних колонок
    extra_columns = set(current_by_name) - set(expected_by_name)
    for col in extra_columns:
      execute(f"DROP COLUMN {col}")


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
    'mysql': update_struct_mysql,
  }.get(config['db']['url'].split(':')[0].split('+')[0], update_struct_default)

  inspector = inspect(engine)
  for table_name in Base.metadata.tables:
    # Получаем текущие столбцы из БД
    existing_columns = {(col['name'], filter_type(col['type']), col['default'])
                        for col in inspector.get_columns(table_name)}
    existing_columns = {(col[0], col[1], get_default_value(col[2], col[1])) for col in existing_columns}

    # Получаем ожидаемые столбцы из модели
    expected_columns = {(col.name, filter_type(col.type), get_default_value(col.default),
                         col.nullable, col.autoincrement == True)
                        for col in Base.metadata.tables[table_name].columns}
    expected_columns = {(col[0], col[1], get_default_value(col[2], col[1]), col[3], col[4]) for col in expected_columns}
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
  print('🔧 Проверка структуры БД завершена')


# Зависимость для получения сессии
def db_session():
  session = SessionLocal()
  try:
    return session
  finally:
    session.close()
