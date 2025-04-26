from models.base_db_model import BaseModelDB
from sqlalchemy import Column, Integer, String
from db_models.common.json import Json
from db_models.common.list import List
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
import re
from typing import Optional
from utils.db_utils import db_session

# Оригинальный справочник ICON_RULES
ICON_RULES = [
  # Новые правила на основе анализа
  {"match": r"^countdown$", "icon": "timer-outline", "label": "Обратный отсчёт"},
  {"match": r"^power_outage_memory$", "icon": "memory", "label": "Память отключения питания"},
  {"match": r"^indicator_mode$", "icon": "lightbulb-on-outline", "label": "Режим индикатора"},
  {"match": r"^backlight_mode$", "icon": "lightbulb", "label": "Режим подсветки"},
  {"match": r"^battery_state$", "icon": "battery", "label": "Состояние батареи"},
  {"match": r"^(learn_ir_code|learned_ir_code|ir_code_to_send)$", "icon": "remote-tv", "label": "ИК-команда"},
  {"match": r"^temperature_(threshold|breaker)$", "icon": "thermometer-alert", "label": "Температурный порог/реле"},
  {"match": r"^power_(threshold|breaker)$", "icon": "flash-alert", "label": "Мощностной порог/реле"},
  {"match": r"^over_current_(threshold|breaker)$", "icon": "current-ac", "label": "Перегрузка по току"},
  {"match": r"^over_voltage_(threshold|breaker)$", "icon": "flash-alert", "label": "Перенапряжение"},
  {"match": r"^under_voltage_(threshold|breaker)$", "icon": "flash-off", "label": "Недонапряжение"},
  {"match": r"^action$", "icon": "play-circle-outline", "label": "Действие"},
  {"match": r"^operation_mode$", "icon": "gesture-tap-button", "label": "Режим работы"},
  {"match": r"^power_on_behavior(_l[0-9])?$", "icon": "power-plug", "label": "Поведение при включении питания"},

  # Существующие старые правила
  {"match": r"^state(_.*)?$", "icon": "power", "label": "Состояние"},
  {"match": r"^switch(_.*)?$", "icon": "toggle-switch", "label": "Переключатель"},
  {"match": r"^(motion|occupancy|presence)$", "icon": "motion-sensor", "label": "Движение"},
  {"match": r"^window(_open)?$", "icon": "window-closed", "label": "Окно"},
  {"match": r"^(gas|co2)$", "icon": "gas-cylinder", "label": "Газ"},
  {"match": r"^pm(2_5|10)$", "icon": "weather-fog", "label": "Частицы PM"},
  {"match": r"^(sound|noise)$", "icon": "volume-high", "label": "Шум"},
  {"match": r"^temperature$", "icon": "thermometer", "label": "Температура"},
  {"match": r"^humidity$", "icon": "water-percent", "label": "Влажность"},
  {"match": r"^illuminance(_lux)?$", "icon": "brightness-5", "label": "Освещённость"},
  {"match": r"^voltage$", "icon": "flash", "label": "Напряжение"},
  {"match": r"^current$", "icon": "current-ac", "label": "Ток"},
  {"match": r"^power$", "icon": "flash-outline", "label": "Мощность"},
  {"match": r"^energy$", "icon": "lightning-bolt", "label": "Энергия"},
  {"match": r"^linkquality$", "icon": "wifi", "label": "Качество связи"},
  {"match": r"^contact$", "icon": "door-closed", "label": "Контакт"},
  {"match": r"^lock$", "icon": "lock", "label": "Замок"},
  {"match": r"^open$", "icon": "door-open", "label": "Открытие"},
  {"match": r"^water_leak$", "icon": "water-alert", "label": "Протечка воды"},
  {"match": r"^smoke$", "icon": "smoke-detector", "label": "Дым"},
  {"match": r"^tamper(_status)?$", "icon": "shield-alert", "label": "Взлом"},
  {"match": r"^vibration$", "icon": "vibrate", "label": "Вибрация"},
  {"match": r"^tilt$", "icon": "angle-acute", "label": "Наклон"},
  {"match": r"^impact$", "icon": "hammer", "label": "Удар"},
  {"match": r"^rotation$", "icon": "rotate-3d-variant", "label": "Поворот"},
  {"match": r"^soil_moisture$", "icon": "water", "label": "Влажность почвы"},
  {"match": r"^pressure$", "icon": "gauge", "label": "Давление"},
  {"match": r"^button$", "icon": "radiobox-marked", "label": "Кнопка"},
  {"match": r"^fan_mode$", "icon": "fan", "label": "Режим вентиляции"},
  {"match": r"^temperature_unit$", "icon": "temperature-celsius", "label": "Единица температуры"},
  {"match": r"^color_temp$", "icon": "thermometer-lines", "label": "Цветовая температура"},
  {"match": r"^color$", "icon": "palette", "label": "Цвет"},
  {"match": r"^brightness$", "icon": "brightness-6", "label": "Яркость"},
  {"match": r"^sensitivity$", "icon": "chart-bell-curve", "label": "Чувствительность"},
  {"match": r"^duration$", "icon": "timer", "label": "Длительность"},
  {"match": r"^signal_strength$", "icon": "access-point", "label": "Уровень сигнала"},
  {"match": r"^status$", "icon": "information-outline", "label": "Статус"},
  {"match": r"^mode$", "icon": "gesture-tap-button", "label": "Режим"},
  {"match": r"^boost$", "icon": "rocket-launch", "label": "Ускорение"},
  {"match": r"^heating$", "icon": "radiator", "label": "Отопление"},
  {"match": r"^cooling$", "icon": "snowflake", "label": "Охлаждение"},
  {"match": r"^window_open_detection$", "icon": "window-closed-variant", "label": "Открытое окно"},
  {"match": r"^child_lock$", "icon": "baby-face", "label": "Блокировка от детей"},
  {"match": r"^battery(_low)?$", "icon": "battery", "label": "Батарея"},
  {"match": r"^(firmware|software)$", "icon": "chip", "label": "Прошивка"},
  {"match": r"^update_available$", "icon": "download", "label": "Обновление доступно"},
  {"match": r"^last_seen$", "icon": "clock", "label": "Последнее обновление"},

  # Климат, освещение, уф, осадки
  {"match": r"^radiation$", "icon": "radioactive", "label": "Радиация"},
  {"match": r"^rain(_.*)?$", "icon": "weather-rainy", "label": "Дождь"},
  {"match": r"^precipitation$", "icon": "weather-pouring", "label": "Осадки"},
  {"match": r"^wind_speed$", "icon": "weather-windy", "label": "Скорость ветра"},
  {"match": r"^wind_direction$", "icon": "compass", "label": "Направление ветра"},
  {"match": r"^uv$", "icon": "weather-sunny-alert", "label": "УФ-индекс"},
  {"match": r"^dew_point$", "icon": "thermometer-alert", "label": "Точка росы"},
  {"match": r"^soil_temperature$", "icon": "thermometer", "label": "Температура почвы"},
  {"match": r"^snow$", "icon": "weather-snowy", "label": "Снег"},

  # Шторы, рольставни
  {"match": r"^time$", "icon": "clock-time-four-outline", "label": "Время"},
  {"match": r"^timer(_.*)?$", "icon": "timer-outline", "label": "Таймер"},
  {"match": r"^curtain(_.*)?$", "icon": "blinds", "label": "Штора"},
  {"match": r"^cover(_.*)?$", "icon": "garage", "label": "Роллеты/ворота"},
  {"match": r"^blind(_.*)?$", "icon": "blinds-horizontal", "label": "Жалюзи"},
  {"match": r"^position$", "icon": "cursor-move", "label": "Позиция"},
  {"match": r"^open_percentage$", "icon": "percent", "label": "Процент открытия"},
]


# Модель таблицы
class PortMetadata(BaseModelDB):
  __tablename__ = "port_metadata"

  _can_view = 'root'
  _can_create = 'root'
  _can_read = 'admin'
  _can_update = 'root'
  _can_get_structure = 'admin'

  id = Column(Integer, primary_key=True, index=True, autoincrement=True)
  name = Column(String(100), index=True, nullable=False)  # property name или маска
  icon = Column(String(100))  # иконка без mdi:
  description = Column(String(255))  # русскоязычное описание
  match = Column(String(255))  # regex-маска для соответствия

  @classmethod
  def find_match(cls,
                 text: str,
                 startswith_only: bool = False,
                 separator: Optional[str] = None) -> Optional["PortMetadata"]:
    if not text:
      return None
    candidates = text.split(separator) if separator else [text]

    with db_session() as db:
      # Получаем все записи из базы
      rules = db.query(cls).all()

    for part in candidates:
      if not part:
        continue
      part = part.strip()
      for rule in rules:
        pattern = rule.match
        if startswith_only:
          if re.match(pattern, part):
            return rule
        else:
          if re.search(pattern, part):
            return rule
    return None

  @classmethod
  def custom_routes(cls, app: FastAPI, db_session):
    # Создание таблицы port_metadata

    with db_session() as db:
      # Проверяем есть ли данные в таблице
      row = db.query(PortMetadata).first()
      if not row:
        for rule in ICON_RULES:
          db.add(PortMetadata(
            name=rule["label"],
            match=rule["match"],
            icon=rule["icon"],
            description=rule["label"] + ' (авто)',
          ))
        db.commit()
