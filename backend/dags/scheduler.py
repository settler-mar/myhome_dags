from models.dag_node import DAGNode
from time import sleep
from time import time
import concurrent.futures
from crontab import CronTab
from datetime import datetime


class SchedulerNode(DAGNode):
  name = 'Scheduler'
  version = '0.0'
  description = 'Запуск сигнала по расписанию. Через set можно заменить {} на любое значение'
  public: bool = True

  prev_scheduler_str = None
  cron: CronTab = None
  run_at = None

  input_groups = []

  params_groups = [
    {'name': 'scheduler',
     'description': 'Расписание в формате cron. Пример: 0 0 * * * or 0 {} * * * *. {} задается в input(set) или вручную',
     'default': '0 0 * * *',
     'type': 'str',
     'public': False
     },
    {'name': 'set',
     'description': 'Замена {} в расписании',
     'type': 'str',
     'default': '0',
     'public': True},
    {'name': 'out_value',
     'description': 'Результат выполнения узла',
     'type': 'select',
     'default': 'on (255)',
     'items': {0: 'off (0)', 255: 'on (255)', 127: 'half/mode (127)'},
     'public': False},
  ]
  output_groups = [
    {'name': 'default', 'description': 'Выход сработки'}
  ]

  sub_title = '{scheduler}'

  def __init__(self):
    super().__init__()
    self.stop_thread()

    self.thread = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    self.thread.submit(self.run_step)

  async def set_param(self, name: str, value: any, send_update: bool = True):
    await DAGNode.set_param(self, name, value, send_update)

  @property
  def scheduler_str(self):
    if '{}' in self.params['scheduler']:
      return self.params['scheduler'].format(self.params['set'])
    return self.params['scheduler']

  def send(self):
    print(datetime.now(), 'SchedulerNode send', id(self))

  def run_step(self):
    if self.prev_scheduler_str != self.scheduler_str:
      self.prev_scheduler_str = self.scheduler_str
      print(datetime.now(), 'SchedulerNode new shadule', id(self), self.scheduler_str)
      self.cron = CronTab(self.params['scheduler'])
      self.run_at = time() + self.cron.next(default_utc=False)

      ts_end_minutes = 6 - time() % 5
      if ts_end_minutes > 1:
        sleep(ts_end_minutes - 1)

    if self.run_at is not None and time() > self.run_at:
      self.send()
      sleep(1)
      self.run_at = time() + self.cron.next(default_utc=False)

    sleep(1)
    if self.thread:
      self.thread.submit(self.run_step)

  def execute(self, input_keys: list):
    print('DelayNode execute', input_keys)
    # Остановка узла
    if 'stop' in input_keys is not None:
      pass

    # Запуск узла
    if 'start' in input_keys:
      pass
