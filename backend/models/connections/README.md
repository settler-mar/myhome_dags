
# 📦 Конфигурация подключения: README

Формат описания типов подключения для универсального интерфейса управления устройствами.

## 🗂 Структура объекта

```json
{
  "code": "my_home",
  "name": "MyHomeClass",
  "type": "myhome",
  "params": { ... },
  "devices_params": { ... },
  "rules": { ... },
  "actions": [ ... ],
  "description": "Опциональное описание",
  "icon": "mdi-home"
}
```

---

## ⚙️ params / devices_params

Описание параметров подключения и устройств.

| Поле         | Тип     | Описание |
|--------------|---------|----------|
| `type`       | string  | `string`, `int`, `bool`, `list`, `str` |
| `description`| string  | Подпись |
| `default`    | any     | Значение по умолчанию |
| `readonly`   | boolean | Только отображение |
| `options`    | object  | (для list) ключ: подпись |
| `min`, `max` | number  | Для чисел |

Пример:
```json
"params": {
  "host": {
    "type": "string",
    "description": "Адрес брокера",
    "default": "localhost"
  }
}
```

---

## 🔐 rules

Права на действия:

```json
"rules": {
  "allow_device_edit": true,
  "allow_device_add": false,
  "allow_device_delete": true,
  "allow_port_edit": false,
  "allow_port_add": false,
  "allow_port_delete": false
}
```

---

## 🚀 actions

Описывает кнопки, меню, модалки, состояния.

### Общие поля

| Поле     | Тип     | Описание |
|----------|---------|----------|
| `name`   | string  | Название кнопки |
| `type`   | string  | `request`, `json_form`, `table_modal`, `state` |
| `scope`  | string  | `connection`, `device`, `port` |
| `icon`   | string  | Иконка mdi |
| `menu`   | boolean | В контекстное меню |

---

### 📡 request

Отправляет запрос на сервер.

```json
{
  "type": "request",
  "method": "POST",
  "endpoint": "/api/devices/{device_id}/restart",
  "confirm": true,
  "input": {
    "delay": {
      "type": "int", "label": "Минуты", "default": 5
    }
  },
  "update_after": "table.devices|table.ports"
}
```

---

### 🧾 json_form

Форма, получаемая с сервера и отправляемая обратно.

```json
{
  "type": "json_form",
  "endpoint": "/api/devices/{device_id}/config",
  "submit_endpoint": "/api/devices/{device_id}/config"
}
```

---

### 📊 table_modal

Таблица с действиями по строкам.

```json
{
  "type": "table_modal",
  "endpoint": "/api/scan",
  "structure": [
    { "name": "ip", "title": "IP" }
  ],
  "refreshable": true,
  "actions": [
    {
      "name": "Добавить",
      "type": "request",
      "method": "GET",
      "endpoint": "/api/add/{ip}",
      "icon": "mdi-plus"
    }
  ]
}
```

---

### 📍 state

Отображает текущее значение (live) из поля.

```json
{
  "type": "state",
  "scope": "device",
  "key": "ip",
  "icon": "mdi-ip-network",
  "show_if_empty": false
}
```

---

## 🧠 input поля (для request)

```json
"input": {
  "mode": {
    "type": "select",
    "label": "Режим",
    "default": "fast",
    "options": {
      "fast": "Быстрый",
      "slow": "Медленный"
    }
  },
  "timeout": {
    "type": "int",
    "label": "Таймаут (сек)",
    "default": 5,
    "min": 0,
    "max": 60
  }
}
```

---

## ✅ Пример использования actions

```json
{
  "name": "Перезапуск",
  "type": "request",
  "scope": "device",
  "endpoint": "/api/devices/{device_id}/restart",
  "method": "POST",
  "confirm": true,
  "icon": "mdi-restart"
}
```

