from models.dag_node import DAGNode
from time import sleep
from time import time
from utils.logs import log_print
from utils.socket_utils import connection_manager


class DelayNode(DAGNode):
  name = 'Delay'
  version = '0.0'
  description = 'Задержка на заданное количество секунд'
  public: bool = True

  input_groups = [
    {'name': 'start', 'description': 'Запустить таймер'},
    {'name': 'stop', 'description': 'Остановить таймер'}
  ]
  params_groups = [
    {'name': 'delay_seconds',
     'description': 'Задержка в секундах',
     'type': 'int',
     'default': 10, 'min': 0, 'max': 36000, 'step': 1,
     'unit': 's',
     'public': True},
    {'name': 'out_value',
     'description': 'Результат выполнения узла',
     'type': 'select',
     'default': -1,
     'items': {-1: 'input(start)', 0: 'off (0)', 255: 'on (255)', 127: 'half/mode (127)'},
     'public': False}
  ]
  output_groups = [
    {'name': 'default', 'description': 'Выходные данные по умолчанию'}
  ]

  sub_title = 'Delay: {delay_seconds} seconds'

  def send_update(self):
    value = self.params.get('out_value', -1)
    if value == -1:
      value = self.input_values.get('start'),

    connection_manager.broadcast_log(
      level='debug',
      message=f"🤖 {self.name} finished at {time()}. Delay: {self.params['delay_seconds']} seconds.",
      permission='root',
      dag_id=id(self),
    )
    # log_print(f"Node {self.name} finished at {time()}. Delay: {self.params['delay_seconds']} seconds.")
    self.set_output(value)

  def execute(self, input_keys: list):
    # Остановка узла
    if 'stop' in input_keys:
      self.stop_thread()
      self.input_values['stop'] = None
      connection_manager.broadcast_log(
        level='debug',
        message=f"Node {self.name} stop.",
        permission='root',
        dag_id=id(self),
      )

    # Запуск узла
    if 'start' in input_keys:
      connection_manager.broadcast_log(
        level='debug',
        message=f"Node {self.name} started at {time()}. Delay: {self.params['delay_seconds']} seconds.",
        permission='root',
        dag_id=id(self),
      )
      self.thread.submit(lambda x: sleep(x), self.params['delay_seconds'])  # Синхронная задержка
      self.thread.submit(lambda x: self.send_update(), 0)  # Асинхронное обновление
