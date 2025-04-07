import os
import inspect
import asyncio
from datetime import datetime, timedelta
from typing import List

LOG_DIR = os.path.abspath('../store/logs')


def log_print(*msg):
  su = 'socket_utils.py' in inspect.stack()[1].filename
  frame = inspect.stack()[2] if su else inspect.stack()[1]
  clicksource = frame.function
  filename = frame.filename.split('/')[-1]
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


def init_routes(app):
  from fastapi import Depends
  from utils.auth import RoleChecker

  clear_logs()  # первая очистка

  @app.on_event("startup")
  async def start_log_cleaner():
    asyncio.create_task(schedule_auto_clear_logs())

  @app.get('/logs/clear',
           response_model=List[dict],
           tags=["live/logs"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def clear_logs_route():
    clear_logs()
    return {'status_code': 200}

  @app.get('/logs/{year}/{month}/{day}/{hour}',
           response_model=List[dict],
           tags=["live/logs"],
           dependencies=[Depends(RoleChecker('admin'))])
  @app.get('/logs/last',
           response_model=List[dict],
           tags=["live/logs"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def get_logs_route(year: int = None, month: int = None, day: int = None, hour: int = None):
    return get_logs(year, month, day, hour)
