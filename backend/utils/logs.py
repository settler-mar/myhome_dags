from datetime import datetime
import inspect


def log_print(*msg):
  su = 'socket_utils.py' in inspect.stack()[1].filename
  frame = inspect.stack()[2] if su else inspect.stack()[1]
  clicksource = frame.function
  filename = frame.filename.split('/')[-1]
  lineno = frame.lineno
  msg = [datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
         '(SU)' if su else None,
         clicksource,
         f'{filename}:{lineno}',
         ' '.join(map(str, msg))]
  print(' - '.join([m for m in msg if m is not None]))
