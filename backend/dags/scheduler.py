from models.dag_node import DAGNode
from time import sleep
from time import time
import concurrent.futures
from crontab import CronTab
from datetime import datetime
from utils.logs import log_print


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
     'items': {0: 'off (0)', 255: 'on (255)', 127: 'half/mode (127)', -1: 'custom'},
     'public': False},
    {
      'name': 'custom_value',
      'description': 'Пользовательское значение',
      'type': 'str',
      'public': True,
      'default': '255'
    }
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
    name in ['scheduler', 'set'] and self.calc_new_schedule()

  @property
  def scheduler_str(self):
    if '{}' in self.params['scheduler']:
      return self.params['scheduler'].format(self.params['set'])
    return self.params['scheduler']

  def send(self):
    value = self.params.get('out_value', -1)
    if value == -1:
      value = self.params.get('custom_value')
    self.updated_output = {}
    self.set_output(value)
    self._run_next()

  def calc_new_schedule(self):
    if self.prev_scheduler_str != self.scheduler_str:
      self.prev_scheduler_str = self.scheduler_str
      log_print(datetime.now(), 'SchedulerNode new shadule', id(self), self.scheduler_str)
      self.run_at = None
      try:
        self.cron = CronTab(self.scheduler_str)
        self.run_at = time() + self.cron.next(default_utc=False)

        ts_end_minutes = 6 - time() % 5
        if ts_end_minutes > 1:
          sleep(ts_end_minutes - 1)
      except Exception as e:
        log_print(datetime.now(), 'SchedulerNode new shadule error', id(self), e)

  def run_step(self):
    self.calc_new_schedule()

    if self.run_at is not None and time() > self.run_at:
      self.send()
      sleep(1)
      self.run_at = time() + self.cron.next(default_utc=False)

    sleep(1)
    if self.thread:
      self.thread.submit(self.run_step)

  def execute(self, input_keys: list):
    pass
