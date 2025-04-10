import os
import inspect
import asyncio
from datetime import datetime, timedelta
from typing import List

LOG_DIR = os.path.abspath('../store/logs')
if not os.path.exists(LOG_DIR):
  os.makedirs(LOG_DIR, exist_ok=True)


def log_print(*msg):
  su = 'socket_utils.py' in inspect.stack()[1].filename
  frame = inspect.stack()[2] if su else inspect.stack()[1]
  clicksource = frame.function
  filename = frame.filename.split('/')[-1]
  if filename == '__init__.py':
    filename = frame.filename.split('/')[-2] + '/'
  lineno = frame.lineno

  timestamp = datetime.now()
  time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
  msg_parts = [
    time_str,
    '(SU)' if su else None,
    clicksource,
    f'{filename}:{lineno}',
    ' '.join(map(str, msg))
  ]
  line = ' - '.join(filter(None, msg_parts))

  print(line)

  # Формируем путь к hourly-логу
  log_path = os.path.join(
    LOG_DIR,
    timestamp.strftime('%Y/%m/%d')
  )
  os.makedirs(log_path, exist_ok=True)

  file_name = f"{timestamp.strftime('%H')}.log"
  full_path = os.path.join(log_path, file_name)

  with open(full_path, 'a', encoding='utf-8') as f:
    f.write(line + '\n')


def get_logs(year=None, month=None, day=None, hour=None):
  logs = []

  # Вернуть последний лог, если параметры не заданы
  if not all([year, month, day, hour]):
    for root, dirs, files in os.walk(LOG_DIR, topdown=False):
      for name in sorted(files, reverse=True):
        if name.endswith('.log'):
          path = os.path.join(root, name)
          with open(path, 'r', encoding='utf-8') as f:
            return f.readlines()

  try:
    path = os.path.join(
      LOG_DIR,
      f"{year:04d}",
      f"{month:02d}",
      f"{day:02d}",
      f"{hour:02d}.log"
    )
    if os.path.exists(path):
      with open(path, 'r', encoding='utf-8') as f:
        logs = f.readlines()
  except Exception as e:
    logs = [f"Error reading logs: {e}"]

  return logs


def clear_logs():
  log_print("Clearing logs older than 30 days")
  threshold = datetime.now() - timedelta(days=30)

  for root, dirs, files in os.walk(LOG_DIR, topdown=False):
    for name in files:
      path = os.path.join(root, name)
      try:
        mtime = datetime.fromtimestamp(os.path.getmtime(path))
        if mtime < threshold:
          os.remove(path)
          log_print(f"Deleted: {path}")
      except Exception as e:
        log_print(f"Error deleting {path}: {e}")
    # Удаление пустых директорий
    if not os.listdir(root):
      try:
        os.rmdir(root)
      except Exception:
        pass


async def schedule_auto_clear_logs():
  while True:
    await asyncio.sleep(20 * 60)  # 20 минут
    clear_logs()


def get_log_tree_partial(year=None, month=None, day=None):
  results = []

  base_path = os.path.join(LOG_DIR)
  if year:
    base_path = os.path.join(base_path, f"{year:04d}")
  if month:
    base_path = os.path.join(base_path, f"{month:02d}")
  if day:
    base_path = os.path.join(base_path, f"{day:02d}")

  if not os.path.exists(base_path):
    return []

  if not year:
    # Возвращаем список лет
    return sorted([d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))])

  if year and not month:
    return sorted([d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))])

  if year and month and not day:
    return sorted([d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))])

  if year and month and day:
    for name in sorted(os.listdir(base_path)):
      if name.endswith('.log') and len(name) == 6:
        hour = name[:2]
        path = os.path.join(base_path, name)

        try:
          size = os.path.getsize(path)
          with open(path, 'r', encoding='utf-8') as f:
            lines = sum(1 for _ in f)
        except Exception:
          size = 0
          lines = 0

        results.append({
          'hour': hour,
          'size': size,
          'lines': lines
        })

  return results


def init_routes(app):
  from fastapi import Depends
  from utils.auth import RoleChecker

  clear_logs()  # первая очистка

  @app.on_event("startup")
  async def start_log_cleaner():
    asyncio.create_task(schedule_auto_clear_logs())

  @app.get('/api/logs/clear',
           tags=["live/logs"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def clear_logs_route():
    clear_logs()
    return {'status_code': 200}

  @app.get('/api/logs/get/{year}/{month}/{day}/{hour}',
           tags=["live/logs"],
           dependencies=[Depends(RoleChecker('admin'))])
  @app.get('/api/logs/last',
           tags=["live/logs"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def get_logs_route(year: int = None, month: int = None, day: int = None, hour: int = None):
    return get_logs(year, month, day, hour)

  @app.get('/api/logs/tree',
           tags=["live/logs"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def tree_root():
    return get_log_tree_partial()

  @app.get('/api/logs/tree/{year}',
           tags=["live/logs"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def tree_year(year: int):
    return get_log_tree_partial(year)

  @app.get('/api/logs/tree/{year}/{month}',
           tags=["live/logs"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def tree_month(year: int, month: int):
    return get_log_tree_partial(year, month)

  @app.get('/api/logs/tree/{year}/{month}/{day}',
           tags=["live/logs"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def tree_day(year: int, month: int, day: int):
    return get_log_tree_partial(year, month, day)
