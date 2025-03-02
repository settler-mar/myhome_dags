from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import asyncio

from datetime import datetime
import json


# Define a custom function to serialize datetime objects
def serialize_datetime(obj):
  if isinstance(obj, datetime):
    return obj.isoformat()
  raise TypeError("Type not serializable")


class ConnectionManager:
  def __init__(self):
    self.active_connections: List[WebSocket] = []

  async def connect(self, websocket: WebSocket):
    await websocket.accept()
    self.active_connections.append(websocket)
    print("Connection established", websocket.client.host)

  def disconnect(self, websocket: WebSocket):
    if websocket in self.active_connections:
      self.active_connections.remove(websocket)

  async def broadcast(self, data: dict):
    print('broadcast', data)
    for connection in self.active_connections:
      try:
        await asyncio.create_task(connection.send_text(json.dumps(data, default=serialize_datetime)))
      except WebSocketDisconnect:
        print("Disconnecting", connection.client.host)
        self.disconnect(connection)


connection_manager = ConnectionManager()
