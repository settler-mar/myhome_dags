from fastapi import Depends, APIRouter, Query
from sqlalchemy.util import await_fallback
from utils.auth import RoleChecker
import paho.mqtt.client as mqtt
import json
from pprint import pprint
from typing import Optional, Union
from utils.db_utils import db_session
from db_models.devices import Devices as DbDevices
from db_models.ports import Ports as DbPorts
from models.connections import Connectors
from models.devices import Devices
from utils.auth import RoleChecker, CurrentUser
import threading
from datetime import datetime, timedelta
from utils.socket_utils import connection_manager
from utils.logs import log_print
from ssdpy import SSDPClient
import asyncio
import aiohttp
import inspect
import time
import os
import requests
import hashlib
from utils.google_connector import GoogleConnector
from ipaddress import ip_address, AddressValueError
from fastapi.responses import JSONResponse


async def fetch_info(session, ip, semaphore):
  url = f"http://{ip}/info"
  async with semaphore:
    try:
      async with session.get(url, timeout=5) as response:
        text = await response.text()
        if response.status == 200:
          data = json.loads(text)
        else:
          data = {"error": f"JSON decode error", "raw_response": text}
        data['ip'] = ip
        return ip, data
    except Exception as e:
      return ip, {"error": str(e)}


class ConfigVersionManager:
  def __init__(self, base_url, device_id, config_dir='/config', backup_root='../store/backup/devices'):
    self.base_url = base_url.rstrip('/')
    self.device_id = device_id
    self.config_dir = config_dir
    self.backup_root = os.path.realpath(os.path.join(backup_root, str(device_id)))
    print(self.backup_root)
    self.log_file = os.path.join(self.backup_root, 'log.json')

    os.makedirs(self.backup_root, exist_ok=True)
    if not os.path.exists(self.log_file):
      with open(self.log_file, 'w') as f:
        json.dump([], f)

  def fetch_file_list(self):
    url = f"{self.base_url}/list?dir={self.config_dir}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()  # Ожидается список путей

  def download_file(self, path):
    print('download file', path)
    url = self.base_url + os.path.join(self.config_dir, path.lstrip('/'))
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.content

  def get_latest_backup_dir(self):
    backups = sorted(
      [d for d in os.listdir(self.backup_root)
       if os.path.isdir(os.path.join(self.backup_root, d)) and d != 'log.json'],
      reverse=True
    )
    if backups:
      return os.path.join(self.backup_root, backups[0])
    return None

  def file_hash(self, content):
    return hashlib.md5(content).hexdigest()

  def load_history(self):
    with open(self.log_file, 'r') as f:
      return json.load(f)

  def save_history_entry(self, timestamp, changed_files):
    history = self.load_history()
    history.append({
      'timestamp': timestamp,
      'changed_files': changed_files
    })
    with open(self.log_file, 'w') as f:
      json.dump(history, f, indent=2)

  def run_backup_if_changed(self):
    file_list = self.fetch_file_list()
    latest_backup_dir = self.get_latest_backup_dir()
    changes_detected = False
    current_files = {}
    changed_files = []

    for file_path in file_list:
      file_path = file_path.get('name')
      content = self.download_file(file_path)
      current_files[file_path] = content

      filename = os.path.basename(file_path)
      if latest_backup_dir:
        old_file_path = os.path.join(latest_backup_dir, filename)
        if os.path.exists(old_file_path):
          with open(old_file_path, 'rb') as f:
            old_content = f.read()
          if self.file_hash(content) != self.file_hash(old_content):
            changes_detected = True
            changed_files.append(filename)
        else:
          changes_detected = True
          changed_files.append(filename)
      else:
        changes_detected = True
        changed_files.append(filename)

    if changes_detected:
      timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
      new_backup_dir = os.path.join(self.backup_root, timestamp)
      os.makedirs(new_backup_dir, exist_ok=True)

      for path, content in current_files.items():
        filename = os.path.basename(path)
        with open(os.path.join(new_backup_dir, filename), 'wb') as f:
          f.write(content)

      self.save_history_entry(timestamp, changed_files)
      print(f"[ConfigVersionManager] ({self.device_id}) Изменения сохранены: {timestamp}")
    else:
      print(f"[ConfigVersionManager] ({self.device_id}) Изменений не обнаружено.")


class MyHomeClass:
  type = 'myhome'
  connectors_list = {}
  _status: str = None
  _devices: dict = {}

  _save_config_hour = 1
  _save_logs_period = 2
  _save_logs_hour = 1
  _save_logs_minute = 1

  params = {
    'save_config_hour': {
      'type': 'int',
      'default': 1,
      'description': 'Час сохранения конфигурации',
      'min': 0,
      'max': 23,
    },
    'save_logs_period': {
      'type': 'int',
      'default': 2,
      'description': 'Период сохранения логов (часы)',
      'min': 1,
      'max': 24,
    },
    '_save_logs_hour': {
      'type': 'int',
      'default': 1,
      'description': 'Час сохранения логов',
      'min': 0,
      'max': 23,
    },
    'save_logs_minute': {
      'type': 'int',
      'default': 2,
      'description': 'Минута сохранения логов',
      'min': 0,
      'max': 59,
    },
    'gsheet': {
      'type': 'str',
      'default': None,
      'description': 'ID Google Sheet для сохранения логов',
    }
  }

  devices_params = {
    'code': {
      'readonly': True,
    },
    'model': {
      'readonly': True,
    },
    'vendor': {
      'readonly': True,
    },
    'type': {
      'readonly': True,
    },
    'params.backup_config': {
      'type': 'bool',
      'default': True,
      'description': 'Сохранять конфигурацию',
    },
    'params.save_logs': {
      'type': 'bool',
      'default': True,
      'description': 'Сохранять логи',
    },
    'params.remove_logs': {
      'type': 'bool',
      'default': True,
      'description': 'Удалять логи после сохранения',
    },
    'params.log_save_method': {
      'type': 'list',
      'default': 'gsheet',
      'description': 'Метод сохранения логов',
      'options': {
        'local_save': 'На сервере',
        'gsheet': 'Google Sheets',
      },
    },
    'params.ip': {
      'type': 'str',
      'default': None,
      'description': 'IP адрес устройства',
      'readonly': True,
    },
    'params.mac': {
      'type': 'str',
      'default': None,
      'description': 'MAC адрес устройства',
      'readonly': True,
    },
    'params.ssid': {
      'type': 'str',
      'default': None,
      'description': 'SSID устройства',
      'readonly': True,
    },
    'params.flash_date': {
      'type': 'str',
      'default': None,
      'description': 'Дата прошивки устройства',
      'readonly': True,
    },
    'params.version': {
      'type': 'str',
      'default': None,
      'description': 'Версия прошивки устройства',
      'readonly': True,
    },
  }

  rules = {
    "allow_device_edit": True,
    "allow_device_add": False,
    "allow_device_delete": True,
    "allow_port_edit": True,
    "allow_port_add": True,
    "allow_port_delete": True
  }

  description = "Модули на основе проекта MyHome. Поддерживает Wi-Fi устройства на основе ESP8266 и ESP32."
  actions = [
    {
      "name": "Устройства MyHome",
      "type": "table_modal",
      "scope": "connection",
      "icon": "mdi-router-wireless",
      "endpoint": "/api/live/connections/myhome/scan",
      "structure": [
        {"name": "ip", "title": "IP адрес"},
        {"name": "mac", "title": "MAC адрес"},
        {"name": "name", "title": "Имя"},
        {"name": "version", "title": "Версия"},
        {"name": "chip_id", "title": "Chip ID"},
        {"name": "flash_chip_revision", "title": "Тип"},
        {"name": "flash_chip_speed", "title": "Скорость"},
        {"name": "flash_date", "title": "Дата прошивки"},
        {"name": "config_name", "title": "Имя конфигурации"},
        {"name": "flash_counter", "title": "Счетчик прошивок"},
        {"name": "flash_heap", "title": "Память"},
        {"name": "fs_name", "title": "Файловая система"},
        {"name": "run_time", "title": "Время работы"},
        {"name": "ssid", "title": "SSID"},
        {"name": "rssi", "title": "RSSI"},
      ],
      "actions": [
        {
          "name": "Добавить",
          "type": "request",
          "method": "GET",
          "endpoint": "/api/live/connections/myhome/{connection_id}/{ip}/add",
          "update_after": "table.devices|table.ports",
          "icon": "mdi-plus",
        },
        {
          "name": "Заменить",
          "type": "request",
          "method": "GET",
          "endpoint": "/api/live/connections/myhome/{connection_id}/{ip}/replace/{device_id}",
          "update_after": "table.devices|table.ports",
          "icon": "mdi-unfold-more-vertical",
          "input": {
            "device_id": {
              "name": "device_id",
              "type": "text",
              "description": "ID устройства",
              "required": True,
              "default": None,
            }
          }
        }
      ],
      "refreshable": True
    },
    {
      "name": "Добавить устройство по IP",
      "type": "request",
      "endpoint": "/api/live/connections/myhome/{connection_id}/{ip}/add",
      "method": "GET",
      "icon": "mdi-plus",
      "scope": "connection",
      "input":
        {
          "ip": {"name": "ip",
                 "type": "text",
                 "description": "IP адрес устройства",
                 "required": True,
                 "default": None,
                 }
        },
      "update_after": "table.devices|table.ports",
    },
    {
      "name": "Заменить",
      "type": "request",
      "method": "GET",
      "endpoint": "/api/live/connections/myhome/{connection_id}/{ip}/replace/{device_id}",
      "update_after": "table.devices|table.ports",
      "icon": "mdi-unfold-more-vertical",
      "input": {
        "ip": {"name": "ip",
               "type": "text",
               "description": "IP адрес устройства",
               "required": True,
               "default": None,
               },
        "device_id": {
          "name": "device_id",
          "type": "text",
          "description": "ID устройства",
          "required": True,
          "default": None,
        }
      }
    },
    {
      "name": "Обновить устройство",
      "type": "request",
      "endpoint": "/api/live/connections/myhome/{connection_id}/{ip}/add",
      "method": "GET",
      "icon": "mdi-refresh",
      "scope": "device",
      "update_after": "table.devices|table.ports",
    },
    {
      "name": "ip",
      "type": "state",
      "scope": "device",
      "color": "orange",
      "icon": "mdi-ip-network",
      "key": "ip",  # from device[params][ip]
      "show_if_empty": False
    }
  ]

  def __init__(self, **kwargs):
    self._id = kwargs.get('id', None)

    self.sheet = kwargs.get('params', {}).get('gsheet')

    self._save_config_hour = int(kwargs.get('params', {}).get('save_config_hour', self._save_config_hour))
    self._save_logs_period = int(kwargs.get('params', {}).get('save_logs_period', self._save_logs_period))
    self._save_logs_hour = int(kwargs.get('params', {}).get('save_logs_hour', self._save_logs_hour))
    self._save_logs_minute = int(kwargs.get('params', {}).get('save_logs_minute', self._save_logs_minute))

    self.thread = threading.Thread(target=self._run, daemon=True)
    self.stop_event = threading.Event()
    self.thread.start()

  def _save_logs_local(self, name, content, device_id, ip):
    logs_root = "../store/backup/logs"
    os.makedirs(logs_root, exist_ok=True)

    # Конкатенируем в файл по имени
    local_path = os.path.join(logs_root, name)
    with open(local_path, "a", encoding="utf-8") as f:
      f.write(content.strip())

    return True

  def _save_logs_gsheet(self, name, content, device_id, ip):
    data = [line.strip().split(',\t') for line in content.split('\n') if line.strip()]
    data = [[*line[:-1], line[-1].replace('.', ',')] for line in data]
    try:
      GoogleConnector().gsheet_add_row(self.sheet, '.'.join(name.split('.')[:-1]), data)
      return True
    except Exception as e:
      print(f"[Logs] Ошибка при сохранении в gsheet: {e}")
      return False

  def _save_logs(self):
    for device_id, device in self._devices.items():
      params = device.params

      if not params.get("save_logs"):
        continue

      method = {
        'local_save': self._save_logs_local,
        'gsheet': self._save_logs_gsheet,
      }[params.get("log_save_method", "gsheet")]
      if method is None:
        continue  # неизвестный метод

      ip = params.get("ip")
      base_url = f"http://{ip}"
      print(f"[Logs] [local_save] Обработка логов с {device_id} ({ip})")

      try:
        # Получаем список файлов из /logs
        response = requests.get(f"{base_url}/list?dir=/logs", timeout=5)
        response.raise_for_status()
        entries = response.json()

        for entry in entries:
          if entry.get("type") != "file":
            continue
          name = entry.get("name")
          if not name.endswith(".txt") or name in ['_.txt', 'clean.txt']:
            continue

          file_path = f"/logs/{name}"
          file_url = f"{base_url}{file_path}"

          # Скачиваем лог
          log_resp = requests.get(file_url, timeout=5)
          log_resp.raise_for_status()
          content = log_resp.text

          if not method(name, content, device_id, ip):
            print('[Logs] Не удалось сохранить лог', name, device_id)
            return

            # Удаляем лог с устройства, если разрешено
          if params.get("remove_logs", True):
            delete_resp = requests.delete(
              f"{base_url}/edit", params={"path": file_path}, timeout=5
            )
            if delete_resp.status_code == 200:
              print(f"[Logs] {name} удалён с {device_id}")
            else:
              print(f"[Logs] Не удалось удалить {name} с {device_id}: {delete_resp.status_code}")

      except Exception as e:
        print(f"[Logs] Ошибка при обработке {device_id}: {e}")

  def _save_config(self):
    for device_id, device in self._devices.items():
      params = device.params or {}
      if not params.get("backup_config"):
        continue

      base_url = f"http://{params.get('ip')}"
      print(f"[Configs] Обрабатываю device {device_id} по адресу {base_url}")

      try:
        ConfigVersionManager(
          base_url=base_url,
          device_id=device_id
        ).run_backup_if_changed()
      except Exception as e:
        print(f"[Configs] Ошибка при обработке {device_id}: {e}")

  def _run_all(self):
    self._save_logs()
    self._save_config()

  def _run(self):
    while not self.stop_event.is_set():
      now = datetime.now()
      next_run_logs = self._get_next_run_time(now)
      next_run_config = now.replace(hour=self._save_config_hour,
                                    minute=0,
                                    second=0,
                                    microsecond=0)
      if next_run_config <= now:
        next_run_config += timedelta(days=1)

      action, next_run = [
        (self._save_logs, next_run_logs),
        (self._save_config, next_run_config),
      ][next_run_logs > next_run_config]
      if next_run_logs == next_run_config:
        action = self._run_all
      wait_seconds = (next_run - now).total_seconds()

      print(f"[my home] Жду до {next_run.strftime('%Y-%m-%d %H:%M:%S')} ({int(wait_seconds)} сек)", action)
      if wait_seconds > 0:
        time.sleep(wait_seconds)

      if not self.stop_event.is_set():
        print(f"[my home] Выполняю задачу в {datetime.now().strftime('%H:%M:%S')}")
        action()

  def _get_next_run_time(self, current_time):
    base_time = current_time.replace(hour=self._save_logs_hour,
                                     minute=self._save_logs_minute,
                                     second=0,
                                     microsecond=0)
    while base_time <= current_time:
      base_time += timedelta(hours=self._save_logs_period)
    return base_time

  def __del__(self):
    print('MyHomeClass __del__')
    self.stop_event.set()
    if self.thread.is_alive():
      self.thread.join()

  def get_info(self):
    return {
      'status': self._status,
      'type': 'myhome',
      'device_count': len(self._devices),
    }

  async def scan(self):
    client = SSDPClient()
    devices = client.m_search("upnp:MHOME")
    ip_list = [driver['location'].split('/')[2].split(':')[0] for driver in devices]

    semaphore = asyncio.Semaphore(8)  # Максимум 5 одновременных запросов
    async with aiohttp.ClientSession() as session:
      tasks = [fetch_info(session, ip, semaphore) for ip in ip_list]
      results = await asyncio.gather(*tasks)
      return [value[1] for value in results]

  def add_device(self, device):
    print('myhome add device', device)
    self._devices[device.id] = device

    # to do add live WS


def add_routes(app):
  log_print('Adding MYHOME routes')

  def get_connection(connector_id: int):
    connections = Connectors()
    connector_id = int(connector_id)
    if connector_id not in connections.connectors:
      return None
    return connections.connectors[connector_id]

  @app.get("/api/live/connections/myhome/scan",
           tags=["live/connections/myhome"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def scan_myhome():
    return await MyHomeClass().scan()

  @app.get("/api/live/connections/myhome/{ip}/get_value",
           tags=["live/connections/myhome"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def get_myhome_value(ip: str):
    """
    Получить значение устройства по IP
    """
    async with aiohttp.ClientSession() as session:
      url = f"http://{ip}/values"
      async with session.get(url) as response:
        if response.status == 200:
          data = await response.text()
          try:
            data = json.loads(data)
          except json.JSONDecodeError as e:
            data = {"error": f"JSON decode error: {str(e)}", "raw_response": data}
        else:
          data = {"error": f"Error: {response.status}"}
        return data

  @app.get("/api/live/connections/myhome/{connection_id}/{ip}/add",
           tags=["live/connections/myhome"],
           dependencies=[Depends(RoleChecker('admin'))])
  @app.get("/api/live/connections/myhome/{connection_id}/{ip}/add",
           tags=["live/connections/myhome"],
           dependencies=[Depends(RoleChecker('admin'))])
  async def add_myhome_value(ip: str, connection_id: int, current_user: CurrentUser):
    """
    Добавить значение устройства по IP
    """
    # Валидация IP-адреса
    try:
      ip_address(ip)
    except Exception as e:
      return JSONResponse({'error': f'Invalid IP address "{ip}"'}, 422)

    connection = get_connection(connection_id)
    if not connection:
      return {'error': f'Connection with id {connection_id} not found'}, 404

    timeout = aiohttp.ClientTimeout(sock_connect=5, total=10)

    async with aiohttp.ClientSession(timeout=timeout) as session:
      try:
        # Получение /values
        url_values = f"http://{ip}/values"
        async with session.get(url_values) as response:
          if response.status != 200:
            return JSONResponse({'error': f"Ошибка при запросе: {url_values}"}, 422)
          text = await response.text()
          try:
            values = json.loads(text)
          except json.JSONDecodeError as e:
            return JSONResponse({'error': f"Ошибка парсинга /values: {str(e)}"}, 422)

        # Получение /info
        url_info = f"http://{ip}/info"
        async with session.get(url_info) as response:
          if response.status != 200:
            return JSONResponse({'error': f"Ошибка при запросе: {url_info}"}, 422)
          text = await response.text()
          try:
            info = json.loads(text)
          except json.JSONDecodeError as e:
            return JSONResponse({'error': f"Ошибка парсинга /info: {str(e)}"}, 422)

      except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        return JSONResponse({'error': f"Ошибка при запросе: {str(e)}"}, 422)

    # Работа с БД
    with db_session() as db:
      db_device = db.query(DbDevices).filter(DbDevices.code == info['chip_id']).first()
      if db_device is None:
        db_device = DbDevices(
          code=info['chip_id'],
          name=info['name'],
          model=info['config_name'],
          updated_by=current_user.id,
          created_by=current_user.id,
          connection_id=connection_id,
          location_id=None,
          vendor='my_home',
          params={'backup_config': True},
          description='',
        )
        db.add(db_device)
        db.commit()
        db.refresh(db_device)

      db_device.updated_by = current_user.id
      db_device.vendor = info.get('fr_name', 'my_home')
      db_device.params.update({
        'ip': ip,
        'mac': info.get('mac'),
        'ssid': info.get('ssid'),
        'flash_date': info.get('flash_date'),
        'version': info.get('version'),
        'save_logs': any(el for el in values if el.get('title') == "LOGS")
      })
      db_device.type = info.get('flash_chip_revision')
      db.commit()
      db.refresh(db_device)

      Devices().add_device(db_device.__dict__)

    return {
      "status": "ok",
      "values": values,
      "info": info,
      "current_user": current_user
    }
