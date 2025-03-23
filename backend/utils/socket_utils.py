from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import asyncio

from datetime import datetime
import json
from utils.logs import log_print


# Define a custom function to serialize datetime objects
def serialize_datetime(obj):
  if isinstance(obj, datetime):
    return obj.isoformat()
  print("Type not serializable", obj)
  raise TypeError("Type not serializable")


class ConnectionManager:
  def __init__(self):
    self.active_connections: List[WebSocket] = []

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
                    port_id: int = None,
                    pin_id: int = None,
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
    data = {
      "type": "log",
      "level": level,
      "permission": permission,
      "message": text or message,
      "device_id": device_id,
      "dag_id": dag_id,
      "dag_port_id": dag_port_id,
      "pin_id": pin_id,
      "port_id": port_id,
      "direction": direction,
      "class_name": str(class_name),
      "value": value,
      "value_raw": value_raw,
      "ts": datetime.now().timestamp()
    }
    data = {k: v for k, v in data.items() if v is not None}
    log_print({k: v for k, v in data.items() if v not in ['permission', 'level', 'ts', 'type']})
    asyncio.run(self.broadcast(data, permission))


connection_manager = ConnectionManager()
