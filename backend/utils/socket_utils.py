from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import asyncio

from datetime import datetime
import json
from utils.logs import log_print
import threading


# Define a custom function to serialize datetime objects
def serialize_datetime(obj):
  if isinstance(obj, datetime):
    return obj.isoformat()
  print("Type not serializable", obj)
  raise TypeError("Type not serializable")


class ConnectionManager:
  logs_queue = []
  logs_history = []
  max_history = 10 ** 5

  def __init__(self):
    self.active_connections: List[WebSocket] = []
    self._thread = threading.Thread(target=self._thread_main, daemon=True)
    self._loop = None
    self._stop_event = threading.Event()
    self._thread.start()

  def _thread_main(self):
    asyncio.set_event_loop(asyncio.new_event_loop())
    self._loop = asyncio.get_event_loop()
    self._loop.create_task(self._process_queue())
    self._loop.run_forever()

  async def _process_queue(self):
    while not self._stop_event.is_set():
      while self.logs_queue:
        try:
          data, permission = self.logs_queue.pop(0)
          self.logs_history.append((data, permission))
          self.logs_history = self.logs_history[-self.max_history:]
          await self.broadcast(data)
        except Exception as e:
          print(f"Error processing item: {e}")
      await asyncio.sleep(0.1)

  async def connect(self, websocket: WebSocket):
    token = websocket.cookies.get("token")
    log_print("Connection established", websocket.client.host, token)
    # todo check auth

    await websocket.accept()
    self.active_connections.append(websocket)

  def disconnect(self, websocket: WebSocket):
    if websocket in self.active_connections:
      self.active_connections.remove(websocket)

  async def broadcast(self, data: dict, permission: str = 'all'):
    # todo send data to all clients by permission
    for connection in self.active_connections:
      try:
        await asyncio.create_task(connection.send_text(json.dumps(data, default=serialize_datetime)))
      except WebSocketDisconnect:
        log_print("Disconnecting", connection.client.host)
        self.disconnect(connection)

  def broadcast_log(self,
                    text: str = None,
                    message: str = None,
                    level: str = 'info',
                    permission: str = 'all',
                    device_id: int = None,
                    dag_id: int = None,
                    dag_port_id: str = None,
                    dag: "DAGNode" = None,
                    port_id: int = None,
                    pin_id: int = None,
                    pin_name: str = None,
                    value: str = None,
                    class_name: str = None,
                    value_raw: str = None,
                    direction: str = None):
    """
    Send log message to all connected clients
    level: 'info', 'warning', 'error', 'debug', 'value'
    permission: 'all', 'admin', 'root'
    direction: 'in', 'out', 'params', None
    """
    if isinstance(value, dict) and 'new_value' in value and len(value['new_value']) == 2:
      value = value['new_value'][0]
    class_name = class_name or (dag and dag.__class__.__name__)
    data = {
      "type": "log",
      "level": level,
      "permission": permission,
      "message": text or message,
      "device_id": device_id,
      "dag_id": dag_id or (dag and dag.id),
      "dag_port_id": dag_port_id,
      "pin_id": pin_id,
      "pin_name": pin_name,
      "port_id": port_id,
      "direction": direction,
      "class_name": str(class_name) if class_name else None,
      "value": value,
      "value_raw": value_raw,
      "ts": datetime.now().timestamp()
    }
    data = {k: v for k, v in data.items() if v is not None}
    log_print({k: v for k, v in data.items() if v not in ['permission', 'level', 'ts', 'type']})
    self.logs_queue.append((data, permission))


connection_manager = ConnectionManager()
