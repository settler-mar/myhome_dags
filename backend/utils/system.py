import psutil
import platform
import socket
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
import docker
import subprocess
import os
import json


def is_port_open(ip: str, port: int, timeout: float = 1.0) -> bool:
  try:
    with socket.create_connection((ip, port), timeout=timeout):
      return True
  except Exception:
    return False


def format_bytes(size):
  for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
    if size < 1024:
      return f"{size:.1f} {unit}"
    size /= 1024
  return f"{size:.1f} PB"


def safe_call(func, default=None):
  try:
    return func()
  except Exception:
    return default


def get_gpu_info():
  try:
    result = subprocess.run(
      ['nvidia-smi', '--query-gpu=name,memory.total,memory.used,utilization.gpu', '--format=csv,noheader,nounits'],
      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=True)
    lines = result.stdout.strip().split('\n')
    gpus = []
    for line in lines:
      name, mem_total, mem_used, util = map(str.strip, line.split(','))
      gpus.append({
        "name": name,
        "memory_total": f"{mem_total} MB",
        "memory_used": f"{mem_used} MB",
        "utilization": f"{util} %"
      })
    return gpus
  except Exception:
    return None


def get_processes():
  processes = []
  for proc in safe_call(psutil.process_iter, default=[]):
    try:
      with proc.oneshot():
        processes.append({
          "pid": proc.pid,
          "name": proc.name(),
          "username": proc.username(),
          "cpu_percent": proc.cpu_percent(interval=None),
          "memory_percent": proc.memory_percent(),
          "status": proc.status(),
          "create_time": datetime.fromtimestamp(proc.create_time()).isoformat()
        })
    except Exception:
      continue
  return processes


def get_wifi_iface():
  networks = {}
  last_iface = None
  keys = ['ifindex', 'wdev', 'addr', 'ssid', 'type', 'channel', 'txpower', ]
  try:
    output = subprocess.check_output(["iw", "dev"], text=True)
    for line in output.replace('\t', ' ').splitlines():
      if "Interface" in line:
        last_iface = line.split()[-1]
        networks[last_iface] = {
          'name': last_iface,
        }
        continue
      if last_iface is None:
        continue
      for key in keys:
        if f' {key} ' in line:
          line = line.split(key)
          if line[0].strip() != '':
            break
          line = line[1]
          if key != 'channel':
            networks[last_iface][key] = line.strip()
            continue
          line = line.split(',')
          networks[last_iface][key] = {'channel': line.pop(0).strip()}
          for item in line:
            item = item.strip().split(':')
            if len(item) == 2:
              networks[last_iface][key][item[0]] = item[1].strip()
            else:
              networks[last_iface][key][item[0]] = True
        if "ssid" in line:
          networks[last_iface]['ssid'] = line.split()[-1]
    return networks
  except Exception:
    return {}


def get_network_interfaces():
  interfaces = []
  wifi_iface = get_wifi_iface() or {}
  for iface, addrs in psutil.net_if_addrs().items():
    iface_data = {
      "name": iface,
      "ip": None,
      "mask": None,
      "mac": None,
      "family": None,
      "link": "unknown"
    }
    for addr in addrs:
      if addr.family == socket.AF_INET:
        iface_data["ip"] = addr.address
        iface_data["mask"] = addr.netmask
        iface_data["family"] = "IPv4"
      elif addr.family == socket.AF_PACKET:
        iface_data["mac"] = addr.address
    try:
      output = subprocess.check_output(["ethtool", iface], stderr=subprocess.DEVNULL).decode()
      iface_data["link"] = "yes" if "Link detected: yes" in output else "no"
    except Exception:
      pass
    if iface in wifi_iface:
      iface_data['wifi'] = wifi_iface[iface]
    # try:
    #   output = subprocess.check_output(["nmcli", "device", "show", iface], stderr=subprocess.DEVNULL).decode()
    #   lines = output.strip().splitlines()
    #   iface_data['params'] = dict()
    #   for line in lines:
    #     key = line[:line.index(':')].strip()
    #     value = line[line.index(':') + 1:].strip()
    #     iface_data['params'][key] = value
    # except Exception:
    #   pass
    interfaces.append(iface_data)
  return interfaces


def get_wifi_networks():
  try:
    iface = get_wifi_iface()
    if not iface:
      return []
    result = subprocess.check_output(["iw", "dev", list(iface.keys())[0], "scan"],
                                     stderr=subprocess.DEVNULL).decode()
  except Exception as e:
    return [{"error": f"scan failed: {e}"}]

  active_ssids = [net['ssid'] for net in iface.values() if 'ssid' in net]

  networks = []
  current = {}
  for line in result.splitlines():
    if line.startswith("BSS "):
      if current:
        networks.append(current)
      current = {
        "bssid": line.split()[1].split('(')[0],
        # "interface": iface,
        'is_active': False,
        'associated': 'associated' in line
      }
      continue
    line = line.strip()
    if line.startswith("*"):
      line = line[1:].strip()
    if line.startswith("SSID:"):
      current["ssid"] = line[6:].strip()
      current["is_active"] = current["ssid"] in active_ssids
    elif line.startswith("freq:"):
      current["freq"] = line.split()[1]
    elif line.startswith("signal:"):
      current["signal_dbm"] = float(line.split()[1])
    elif line.startswith("DS Parameter set: channel"):
      current["channel"] = line.split()[-1]
    elif "WPA:" in line or "RSN:" in line:
      current["security"] = "secured"
    elif "no security" in line or "capability: ESS" in line:
      current.setdefault("security", "open")
    elif line.startswith("last seen:"):
      if 'boottime' in line:
        current["boottime"] = line.split()[2].replace('s', '')
      current["last_seen_ms"] = line.split()[2]
    elif line.startswith("Supported rates:") or line.startswith("Extended supported rates:"):
      current.setdefault("rates", []).extend([
        float(rate.strip('*')) for rate in line.split(':', 1)[1].strip().split()
        if rate.replace('.', '').replace('*', '').isdigit()
      ])
    elif line.startswith("Manufacturer:"):
      current["manufacturer"] = line.split(":", 1)[1].strip()
    elif line.startswith("Model:"):
      current["model"] = line.split(":", 1)[1].strip()
    elif line.startswith("Device name:"):
      current["device_name"] = line.split(":", 1)[1].strip()
    elif line.startswith("Serial Number:"):
      current["serial_number"] = line.split(":", 1)[1].strip()
    elif line.startswith("Primary Device Type:"):
      current["device_type"] = line.split(":", 1)[1].strip()
    elif line.startswith("Config methods:"):
      current["wps_config_methods"] = [m.strip() for m in line.split(":", 1)[1].split(",")]
    elif line.startswith("WPS:"):
      current["wps"] = True
  if current:
    networks.append(current)

  return networks


def get_wifi_networks_nmcli():
  try:
    result = subprocess.check_output(["nmcli", "dev", "wifi", "list"]).decode()
    lines = result.split('\n')
    _header = ' ' + lines.pop(0) + ' '
    header = {key: _header.index(' ' + key + ' ') for key in _header.split()}
    header_keys = list(header.keys()) + ['_']
    _header += '_'
    header = {key.lower(): [pos, _header.index(' ' + header_keys[index + 1], pos + 1)]
              for index, (key, pos) in enumerate(header.items())}
    networks = []
    for line in lines:
      if line.strip():
        network = {}
        for key, index in header.items():
          network[key] = line[index[0]:index[1]].strip()
          if key == 'in-use':
            network[key] = True if network[key] == '*' else False
        networks.append(network)
    return networks
  except Exception:
    return []


def get_network_info():
  return {
    "hostname": socket.gethostname(),
    "interfaces": get_network_interfaces(),
    "wifi_networks": get_wifi_networks(),
    "io": {
      iface: psutil.net_io_counters(pernic=True)[iface]._asdict()
      for iface in psutil.net_if_stats().keys()
    },
    "connections": [
      {
        "fd": c.fd,
        "family": str(c.family),
        "type": str(c.type),
        "laddr": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "",
        "raddr": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "",
        "status": c.status,
        "pid": c.pid
      }
      for c in psutil.net_connections(kind='inet')
      if c.status != 'NONE'
    ]
  }


def get_system_info():
  cpu_freq = safe_call(psutil.cpu_freq)
  sensors_temps = safe_call(psutil.sensors_temperatures, default={})
  sensors_fans = safe_call(psutil.sensors_fans, default={})
  battery = safe_call(psutil.sensors_battery, default=None)

  return {
    "hostname": socket.gethostname(),
    "platform": platform.platform(),
    "os": {
      "system": platform.system(),
      "release": platform.release(),
      "version": platform.version(),
      "architecture": platform.machine(),
    },
    "cpu": {
      "physical_cores": psutil.cpu_count(logical=False),
      "logical_cores": psutil.cpu_count(logical=True),
      "frequency_mhz": cpu_freq._asdict() if cpu_freq else {},
      "per_core_usage_percent": psutil.cpu_percent(percpu=True),
      "load_avg_1_5_15": safe_call(psutil.getloadavg, default=[]),
    },
    "memory": safe_call(lambda: psutil.virtual_memory()._asdict(), default={}),
    "swap": safe_call(lambda: psutil.swap_memory()._asdict(), default={}),
    "disks": {
      # "partitions": [
      #   {
      #     "device": p.device,
      #     "mountpoint": p.mountpoint,
      #     "fstype": p.fstype,
      #     "opts": p.opts,
      #     "usage": psutil.disk_usage(p.mountpoint)._asdict(),
      #     "stat": {
      #       "total_inodes": st.f_files,
      #       "free_inodes": st.f_ffree,
      #       "block_size": st.f_bsize,
      #       "fragment_size": st.f_frsize
      #     }
      #   }
      #   for p in psutil.disk_partitions(all=False)
      #   if (st := safe_call(lambda: os.statvfs(p.mountpoint))) is not None
      # ],
      "io": psutil.disk_io_counters()._asdict(),
      # "devices": [
      #   {
      #     "device": name,
      #     "read_count": io.read_count,
      #     "write_count": io.write_count,
      #     "read_bytes": io.read_bytes,
      #     "write_bytes": io.write_bytes
      #   }
      #   for name, io in psutil.disk_io_counters(perdisk=True).items()
      # ],
      "physical": [
        {
          "name": info.get('name', info.get('kname', "")),
          "size": int(info.get("size", info.get('SIZE', 0))),
          "model": info.get('model', info.get("MODEL", "unknown")),
          "serial": info.get('serial', info.get("SERIAL", "")),
          "rotational": info.get('rota', info.get("ROTA", True)),
          "partitions": [
            {
              "name": part["name"],
              "mountpoint": part.get("mountpoint", None),
              "size": int(part.get("size", 0)),
              "uuid": part.get("uuid", None),
              "fstype": part.get("fstype", None),
              "label": part.get("label", None),
              'fsused': int(part.get("fsused", 0)),
            }
            for part in info.get("children", [])
          ]
        }
        for info in safe_call(
          lambda: json.loads(
            __import__("subprocess")
            .check_output(["lsblk", "-O", "-J", "-b"])
            .decode("utf-8")
          )["blockdevices"],
          default=[]
        )
        if info.get("type") == "disk"
      ]
    },
    "network": {
      # "interfaces": {
      #   iface: [addr.address for addr in addrs if addr.family == socket.AF_INET]
      #   for iface, addrs in safe_call(psutil.net_if_addrs, default={}).items()
      # },
      'interfaces': get_network_interfaces(),
      # "wifi_networks": get_wifi_networks(),
      # "io": {
      #   iface: counters._asdict()
      #   for iface, counters in safe_call(lambda: psutil.net_io_counters(pernic=True), default={}).items()
      # },
      "connections": [
        {
          "fd": c.fd,
          "family": str(c.family),
          "type": str(c.type),
          "laddr": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "",
          "raddr": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "",
          "status": c.status,
          "pid": c.pid
        }
        for c in safe_call(lambda: psutil.net_connections(kind='inet'), default=[])
        if c.status != 'NONE'
      ]
    },
    "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
    "uptime_minutes": int((datetime.now().timestamp() - psutil.boot_time()) / 60),
    "users": [u._asdict() for u in safe_call(psutil.users, default=[])],
    "sensors": {
      "temperatures": {
        k: [s._asdict() for s in v] for k, v in sensors_temps.items()
      } if sensors_temps else None,
      "fans": {
        k: [f._asdict() for f in v] for k, v in sensors_fans.items()
      } if sensors_fans else None,
      "battery": battery._asdict() if battery else None
    },
    "gpu": get_gpu_info(),
    "processes": get_processes()
  }


def get_docker_info():
  try:
    client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    containers_info = []

    for container in client.containers.list(all=True):
      try:
        stats = container.stats(stream=False)
        memory_usage = stats['memory_stats'].get('usage', 0)
        memory_limit = stats['memory_stats'].get('limit', 0)
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats'].get('system_cpu_usage', 0) - stats['precpu_stats'].get('system_cpu_usage', 0)
        cpu_usage_percent = (cpu_delta / system_delta * len(
          stats['cpu_stats']['cpu_usage'].get('percpu_usage', []))) * 100 if system_delta > 0 else 0

        net_settings = container.attrs.get('NetworkSettings', {})
        ports = net_settings.get('Ports', {}) or {}
        networks = {
          name: conf.get('IPAddress')
          for name, conf in net_settings.get('Networks', {}).items()
        }

        open_ports = []
        for container_port, mappings in ports.items():
          if mappings:
            for m in mappings:
              host_ip = m.get("HostIp", "127.0.0.1")
              host_port = int(m.get("HostPort", 0))
              status = "open" if is_port_open(host_ip, host_port) else "closed"
              open_ports.append({
                "host_ip": host_ip,
                "host_port": host_port,
                "container_port": container_port,
                "status": status
              })

        containers_info.append({
          "id": container.short_id,
          "name": container.name,
          "status": container.status,
          "image": container.image.tags,
          "uptime": container.attrs['State'].get('StartedAt'),
          "restart_policy": container.attrs['HostConfig'].get('RestartPolicy'),
          "cpu_usage_percent": round(cpu_usage_percent, 2),
          "memory_usage": f"{format_bytes(memory_usage)} / {format_bytes(memory_limit)}",
          "ports": ports,
          "open_ports": open_ports,
          "networks": networks,
          "mounts": [
            m['Source'] + " → " + m['Destination'] for m in container.attrs.get('Mounts', [])
          ],
          "resources": {
            "cpu_limit": container.attrs['HostConfig'].get("NanoCpus", 0),
            "mem_limit": container.attrs['HostConfig'].get("Memory", 0)
          }
        })
      except Exception:
        continue

    system = client.info()
    version = client.version()
    docker_host_info = {
      "docker_version": version.get("Version"),
      "api_version": version.get("ApiVersion"),
      "os": system.get("OperatingSystem"),
      "arch": system.get("Architecture"),
      "containers": {
        "total": system.get("Containers"),
        "running": system.get("ContainersRunning"),
        "paused": system.get("ContainersPaused"),
        "stopped": system.get("ContainersStopped"),
      },
      "images": system.get("Images"),
      "storage_driver": system.get("Driver"),
      "network_driver": system.get("NetworkDriver"),
      "volumes": system.get("Volumes"),
      "plugins": system.get("Plugins"),
    }

    return {
      "host": docker_host_info,
      "containers": containers_info
    }

  except Exception as e:
    return {"error": str(e)}


def get_system_status():
  return {
    "cpu": {
      "usage": psutil.cpu_percent(interval=1),
      "cores": psutil.cpu_count(logical=False),
      "logical_cores": psutil.cpu_count(logical=True)
    },
    "memory": {
      "total": format_bytes(psutil.virtual_memory().total),
      "available": format_bytes(psutil.virtual_memory().available),
      "used": format_bytes(psutil.virtual_memory().used),
      "percent": psutil.virtual_memory().percent
    },
    "disk": {
      "total": format_bytes(psutil.disk_usage('/').total),
      "used": format_bytes(psutil.disk_usage('/').used),
      "free": format_bytes(psutil.disk_usage('/').free),
      "percent": psutil.disk_usage('/').percent
    }
  }


def add_route(app: FastAPI):
  from utils.auth import RoleChecker
  dependencies = [Depends(RoleChecker('admin'))]

  @app.get("/api/status/system", tags=["status"], dependencies=dependencies, response_class=JSONResponse)
  def system_status():
    return get_system_info()

  @app.get("/api/status/system_status", tags=["status"], dependencies=dependencies, response_class=JSONResponse)
  def system_status():
    return get_system_status()

  @app.get("/api/status/docker", tags=["status"], dependencies=dependencies, response_class=JSONResponse)
  def docker_status():
    try:
      return get_docker_info()
    except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))

  @app.get("/api/status/plain", dependencies=dependencies, response_class=PlainTextResponse)
  def system_plain():
    try:
      info = get_system_info()
      return (
        f"Host: {info['hostname']}\n"
        f"Uptime (min): {info['uptime_minutes']}\n"
        f"CPU load (1m): {info['cpu']['load_avg_1_5_15'][0] if info['cpu'].get('load_avg_1_5_15') else 'n/a'}\n"
        f"Memory usage: {info['memory'].get('percent', 'n/a')}%\n"
      )
    except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))

  @app.get("/api/status/wifi", tags=["status"], dependencies=dependencies, response_class=JSONResponse)
  def wifi_status():
    return get_wifi_networks()

  @app.get("/api/status/network", tags=["status"], dependencies=dependencies, response_class=JSONResponse)
  def network_status():
    try:
      return get_network_info()
    except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))
