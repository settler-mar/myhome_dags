from datetime import datetime
import inspect


def log_print(*msg):
  frame = inspect.stack()[1]
  clicksource = frame.function
  filename = frame.filename.split('/')[-1]
  lineno = frame.lineno
  print(f"{datetime.now()} - {clicksource} - {filename}:{lineno} - {' '.join(map(str, msg))}")
