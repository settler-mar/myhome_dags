from typing import List, Optional, Any, Union
import multiprocessing
import concurrent.futures

from utils.socket_utils import connection_manager
from utils.logs import log_print
import os
from datetime import datetime
import asyncio


class DAGNode:
  """
  Базовый класс для узлов (вершин) в Directed Acyclic Graph (DAG).
  Каждый узел может иметь входы, выходы, и может быть асинхронным.

  Метаинформация будет доступна через свойства:
  - name: Имя узла.
  - version: Версия узла.
  - description: Описание узла.
  """
  name: str = 'DAGNode'
  version: str = '0.0'
  description: str = 'Базовый класс для узлов в Directed Acyclic Graph (DAG)'
  sub_title: str = ''
  public: bool = False
  code: str = ''

  input_groups = []  # Группы входов
  params_groups = []  # Группы параметров
  output_groups = []  # Группы выходов

  thread = None

  position = None
  page = 'main'
  is_simple = False

  outputs: dict = None  # Выходы узла (ссылки на другие узлы)
  input_values: dict = None  # Значения входов (параметры)
  updated_output: dict = None  # Обновленные значения выходов. Для передачи на следующий узел. Очищается после передачи

  def __init__(self):
    self.outputs = {}  # Выходы узла (ссылки на другие узлы)
    self.input_values = {}  # Значения входов (параметры)
    self.updated_output = {}  # Обновленные значения выходов

    self.params = {param['name']: param.get('default', None) for param in (self.params_groups or {})}
    self.position = [100, 100]

    if not self.code:
      self.code = self.code or self.name

  def kill(self):
    """Останавливает выполнение узла"""
    self.stop_thread()

  @property
  def id(self):
    return id(self)

  def setPage(self, page: str):
    self.page = page

  def set_simple(self):
    self.is_simple = True

  async def add_output(self,
                       input_node: int,
                       input_type: str = 'in',  # in - вход, params - параметры
                       output_group: Optional[str] = 'default',
                       input_child_group: Optional[str] = 'default',
                       send_update: bool = True):
    """Добавляет выходной узел"""
    if output_group not in self.outputs:
      self.outputs[output_group] = []

    if isinstance(input_node, int):
      from orchestrator.orchestrator import Orchestrator
      input_node = Orchestrator().dags[input_node]

    self.outputs[output_group].append((input_type, input_node, input_child_group))
    if send_update:
      await self.send_update()

  def remove_output(self, input_node: "DAGNode", output_group: Optional[str] = 'default',
                    input_child_group: Optional[str] = 'default', to_type: str = 'in', all_groups: bool = False,
                    send_update: bool = True):
    """Удаляет выходной узел"""
    output_groups = [output_group] if not all_groups else self.outputs.keys()
    self.stop_thread()
    for output_group in output_groups:
      if output_group not in self.outputs:
        continue
      self.outputs[output_group] = [(dag_input_type, dag_input_node, dag_input_child_group)
                                    for dag_input_type, dag_input_node, dag_input_child_group in
                                    self.outputs[output_group]
                                    if dag_input_node.id != input_node.id or
                                    dag_input_child_group != input_child_group or
                                    dag_input_type != to_type]
    if send_update:
      asyncio.create_task(self.send_update())

  async def send_update(self):
    data = {"type": "dag", "action": "update", "data": self.get_json()}

    return await connection_manager.broadcast(data)

  async def set_param(self, name: str, value: any, send_update: bool = True):
    """Устанавливает параметр узла"""
    try:
      if name not in self.params:
        log_print(f"💥 {self} {id(self)} Error: Param {name} not found. Value {value}")
        return
      for param in self.params_groups:
        if param['name'] != name:
          continue
        if 'type' in param:
          value = {
            'int': int,
            'float': float,
            'str': str,
            'bool': bool,
          }.get(param['type'], lambda x: x)(value)
        if 'min' in param and value < param['min']:
          value = param['min']
        if 'max' in param and value > param['max']:
          value = param['max']
        if 'step' in param and (value - param['min']) % param['step'] != 0:
          value = param['min'] + ((value - param['min']) // param['step']) * param['step']

      self.params[name] = value
      if send_update:
        await connection_manager.broadcast({"type": "dag",
                                            "action": "update_params",
                                            "data": {"id": self.id, "params": {name: value}}})
      connection_manager.broadcast_log(level='value',
                                       message='🤛 set dag param',
                                       permission='root',
                                       direction='params',
                                       dag=self,
                                       dag_port_id=name,
                                       value=value)
      # log_print('🤛 set dag param', id(self), self.__class__, name, value)

    except Exception as e:
      log_print(f"Error setting param {name}={value}: {e}")

  async def set_params(self, params: dict, send_update: bool = True):
    """Устанавливает параметры узла"""
    for name, value in params.items():
      await self.set_param(name, value, False)
    if send_update:
      await connection_manager.broadcast(
        {"type": "dag", "action": "update_params", "data": {"id": self.id, "params": self.params}})

  def set_position(self, x: int, y: int):
    """Устанавливает позицию узла"""
    self.position = [x, y]

  def set_input(self, value: Any, input_group: Optional[str] = 'default', comment: str = None):
    """Устанавливает входной узел (перезаписывает предыдущие)"""
    self.input_values[input_group] = value
    connection_manager.broadcast_log(level='value',
                                     message='🤛 set dag input' if comment is None else f'🤛 {comment}',
                                     permission='root',
                                     direction='in',
                                     dag=self,
                                     dag_port_id=input_group,
                                     value=value)

  def set_value(self, port_name: str, value: Union[str, int], comment: str = 'manual'):
    """Устанавливает значение входного порта"""
    value = {
      'key': [comment],
      'new_value': (value, datetime.now().timestamp()),
    }
    self.set_input(value, port_name, comment)
    self.process([port_name])

  def set_output(self, value: Any, output_group: Optional[str] = 'default'):
    """Устанавливает выходной узел (перезаписывает предыдущие)"""
    if isinstance(value, tuple) and len(value) == 1 and isinstance(value[0], dict) and 'new_value' in value[0]:
      value = value[0]
    elif not isinstance(value, dict) or 'new_value' not in value:
      log_print(f"💥 add wrapper for {value}")
      value = {
        'key': [],
        'new_value': (value, datetime.now().timestamp()),
      }

    self.updated_output[output_group] = {
      'key': (*value['key'], id(self)),
      'new_value': value['new_value'],
    }
    connection_manager.broadcast_log(level='value',
                                     message='🤜 set dag output',
                                     permission='root',
                                     direction='out',
                                     dag=self,
                                     dag_port_id=output_group,
                                     value=value['new_value'][0])

  def get_json(self) -> dict:
    """Получение метаинформации об узле в формате JSON."""
    return {key: value for key, value in {'id': self.id,
                                          'name': self.name,
                                          'code': self.code,
                                          'outputs': {name: [(el[0], el[1].id, el[2]) for el in item]
                                                      for name, item in self.outputs.items()},
                                          'params': self.params,
                                          'position': self.position,
                                          'title': self.get_title(),
                                          'version': self.version,
                                          'sub_title': self.sub_title,
                                          'page': self.page,
                                          'is_simple': self.is_simple,
                                          'pins': self.points if hasattr(self, 'points') else None,
                                          }.items() if value is not None}

  def get_title(self) -> str:
    """Получение заголовка узла."""
    return self.name

  def get_sub_title(self) -> str:
    """Получение подзаголовка узла."""
    return ''

  def execute(self, input_keys: list):
    """логика выполнения узла. Будет переопределена в наследуемых классах."""
    raise NotImplementedError("Метод execute должен быть реализован в наследуемом классе.")

  def _execute(self, input_keys: list):
    """Метод для выполнения логики узла и передачи данных на выход."""
    self.updated_output = {}
    self.execute(input_keys)
    # self._run_next()
    # self.thread.shutdown(wait=False)
    # self.thread = None

  def _run_next(self):
    log_print('🏃 run next', id(self), self.__class__)
    need_run = {}
    # Передача данных на выход
    for output_group, value in self.updated_output.items():
      for input_type, output_node, children_group in self.outputs.get(output_group, []):
        try:
          if input_type == 'in':
            output_node.set_input(value, children_group)
            key = (id(output_node), output_node)
            if key not in need_run:
              need_run[key] = set()
            need_run[key].add(children_group)
          elif input_type == 'param':
            val = value.get('new_value', [0, 0])[0]
            asyncio.run(output_node.set_param(children_group, val))
          else:
            log_print(f"💥 {self} {id(self)} Unknown input type {input_type} for {output_node}")
        except Exception as e:
          log_print(f"💥 {self} {id(self)} Error setting output {output_node}: {e}")

    # Запуск следующих в отдельном потоке
    for _node, keys in need_run.items():
      try:
        _node[1].process(keys)
      except Exception as e:
        log_print(f"💥 {self} {id(self)} Error running {_node}: {e}")
    log_print('🏁 run next', id(self), self)

  def stop_thread(self):
    try:
      if self.thread is not None:
        self.thread.shutdown(wait=False, cancel_futures=True)
    except Exception as e:
      pass
    self.thread = None

  def process(self, input_keys: list):
    """Процесс обработки данных или выполнения операций с входами и выходами."""
    # if self.thread is not None and self.thread.is_alive():
    #   self.thread.terminate()
    #
    # self.thread = multiprocessing.Process(target=self._execute)
    # self.thread.start()
    log_print('🤸 process', id(self), self.__class__, input_keys)

    self.stop_thread()

    self.thread = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    self._execute(input_keys)
    self.thread.submit(self._run_next)

  def __repr__(self):
    return f"<DAGNode(name={self.name}, version={self.version})>"

  def __del__(self):
    self.kill()
