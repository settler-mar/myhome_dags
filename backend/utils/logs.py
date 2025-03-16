import datetime
import inspect

def log_print(*msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    frame = inspect.stack()[1]
    clicksource = frame.function
    filename = frame.filename.split('/')[-1]
    lineno = frame.lineno
    print(f"{timestamp} - {clicksource} - {filename}:{lineno} - {' '.join(map(str, msg))}")
