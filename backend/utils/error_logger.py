import os
import sys
import hashlib
import traceback
import linecache
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
import multiprocessing
from utils.configs import config
import threading
import multiprocessing
import functools
import sys
from starlette.background import BackgroundTasks

# 🔧 Конфигурация
ENABLED = config['error_logger'].get('enabled', True)
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../store/error_logs"))
LOG_TTL_DAYS = config['error_logger'].get('ttl_days', 7)
MAX_LOGS_PER_GROUP = config['error_logger'].get('max_logs_per_group', 100)

if ENABLED:
  os.makedirs(LOG_DIR, exist_ok=True)


def cleanup_old_logs():
  if not ENABLED:
    return
  now = datetime.utcnow()
  for group in os.listdir(LOG_DIR):
    group_path = os.path.join(LOG_DIR, group)
    if os.path.isdir(group_path):
      files = sorted(
        (f for f in os.listdir(group_path) if f.endswith('.log')),
        reverse=True
      )
      for file in files:
        try:
          ts = datetime.fromisoformat(file.replace('.log', ''))
          if now - ts > timedelta(days=LOG_TTL_DAYS):
            os.remove(os.path.join(group_path, file))
        except Exception:
          continue
      if len(files) > MAX_LOGS_PER_GROUP:
        for file in files[MAX_LOGS_PER_GROUP:]:
          os.remove(os.path.join(group_path, file))

  # 🧠 Оборачиваем background tasks
  original_add_task = BackgroundTasks.add_task

  def patched_add_task(self, func, *args, **kwargs):
    def wrapped_func(*a, **kw):
      try:
        return func(*a, **kw)
      except Exception:
        log_exception(*sys.exc_info())
        raise

    return original_add_task(self, wrapped_func, *args, **kwargs)

  BackgroundTasks.add_task = patched_add_task


def log_exceptions(fn):
  @functools.wraps(fn)
  def wrapper(*args, **kwargs):
    try:
      return fn(*args, **kwargs)
    except Exception:
      log_exception(*sys.exc_info())
      raise

  return wrapper


def hash_traceback(exc_type, tb):
  lines = []
  while tb:
    frame = tb.tb_frame
    func = frame.f_code.co_name
    context_line = linecache.getline(frame.f_code.co_filename, tb.tb_lineno).strip()
    lines.append(f"{func}:{context_line}")
    tb = tb.tb_next
  key = f"{exc_type.__name__}:" + '|'.join(lines)
  return hashlib.md5(key.encode()).hexdigest()


def extract_context(tb):
  while tb.tb_next:
    tb = tb.tb_next
  frame = tb.tb_frame
  return {
    "filename": frame.f_code.co_filename,
    "lineno": tb.tb_lineno,
    "context_line": linecache.getline(frame.f_code.co_filename, tb.tb_lineno).strip(),
    "locals": frame.f_locals
  }


def log_exception(exc_type, exc_value, tb, extra_context=None):
  if not ENABLED:
    return
  cleanup_old_logs()

  tb_hash = hash_traceback(exc_type, tb)
  context = extract_context(tb)
  formatted = ''.join(traceback.format_exception(exc_type, exc_value, tb))

  group_path = os.path.join(LOG_DIR, tb_hash)
  os.makedirs(group_path, exist_ok=True)

  timestamp = datetime.utcnow().isoformat()
  log_path = os.path.join(group_path, f"{timestamp}.log")

  with open(log_path, "w", encoding="utf-8") as f:
    f.write(f"[Time]: {timestamp}\n")
    f.write(f"[Exception]: {exc_type.__name__}: {exc_value}\n")
    f.write(f"[File]: {context['filename']}:{context['lineno']}\n")
    f.write(f"[Code]: {context['context_line']}\n")
    f.write("[Locals]:\n")
    for k, v in context['locals'].items():
      f.write(f"  {k} = {repr(v)}\n")

    if extra_context:
      f.write("\n[Request Context]:\n")
      for k, v in extra_context.items():
        f.write(f"{k}: {repr(v)}\n")

    f.write("\n[Traceback]:\n")
    f.write(formatted)

  print(f"[!] Exception logged to: {log_path}")


def init_error_handling():
  if not ENABLED:
    return

  sys.excepthook = log_exception

  def mp_excepthook(args):
    log_exception(args.exc_type, args.exc_value, args.exc_traceback)

  multiprocessing.excepthook = mp_excepthook

  original_run = threading.Thread.run

  def patched_run(self):
    try:
      original_run(self)
    except Exception:
      log_exception(*sys.exc_info())
      raise

  threading.Thread.run = patched_run


def add_route(app: FastAPI):
  from fastapi import Depends, HTTPException
  from utils.auth import RoleChecker
  from fastapi.responses import JSONResponse, PlainTextResponse

  @app.exception_handler(Exception)
  async def global_exception_handler(request: Request, exc: Exception):
    # Логируем исключение + контекст запроса
    tb = sys.exc_info()[2]

    # Собираем детали
    context = {
      "url": str(request.url),
      "method": request.method,
      "headers": dict(request.headers),
      "cookies": request.cookies,
      "client": request.client.host if request.client else None,
    }

    try:
      context["query_params"] = dict(request.query_params)
    except Exception:
      pass

    # Передаём в логгер (можно изменить интерфейс log_exception чтобы принимать context)
    log_exception(*sys.exc_info(), extra_context=context)

    return JSONResponse(
      status_code=500,
      content={"detail": "Internal server error"},
    )

  @app.get("/api/errors", tags=["ErrorLogs"], dependencies=[Depends(RoleChecker('admin'))])
  def list_groups():
    """Список хэшей-групп ошибок"""
    if not os.path.exists(LOG_DIR):
      return []

    result = []
    for group_id in sorted(os.listdir(LOG_DIR)):
      group_path = os.path.join(LOG_DIR, group_id)
      if not os.path.isdir(group_path):
        continue

      log_files = sorted(
        [f for f in os.listdir(group_path) if f.endswith(".log")],
        reverse=True
      )

      if not log_files:
        continue

      latest_file = log_files[0]
      latest_path = os.path.join(group_path, latest_file)
      preview = ""
      try:
        with open(latest_path, "r", encoding="utf-8") as f:
          for line in f:
            if line.startswith("[Exception]"):
              preview = line.strip()
              break
      except Exception:
        preview = "(error reading log)"

      result.append({
        "id": group_id,
        "latest": latest_file.replace(".log", ""),
        "count": len(log_files),
        "preview": preview,
        "files": log_files
      })

    return result

  @app.get("/api/errors/{group_id}", tags=["ErrorLogs"], dependencies=[Depends(RoleChecker('admin'))])
  def list_logs(group_id: str):
    """Список логов в группе"""
    group_path = os.path.join(LOG_DIR, group_id)
    if not os.path.isdir(group_path):
      raise HTTPException(status_code=404, detail="Group not found")
    return sorted(os.listdir(group_path), reverse=True)

  @app.get("/api/errors/{group_id}/{log_file}", response_class=PlainTextResponse,
           tags=["ErrorLogs"], dependencies=[Depends(RoleChecker('admin'))])
  def read_log(group_id: str, log_file: str):
    """Содержимое конкретного лога"""
    file_path = os.path.join(LOG_DIR, group_id, log_file)
    if not os.path.exists(file_path):
      raise HTTPException(status_code=404, detail="Log file not found")
    with open(file_path, "r", encoding="utf-8") as f:
      return f.read()
