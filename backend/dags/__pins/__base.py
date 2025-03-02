from models.dag_node import DAGNode


class BasePin(DAGNode):
  version = None
  description = None
  public: bool = False

  params_groups = [{'name': 'pin_id',
                    'description': 'Результат выполнения узла',
                    'type': 'int',
                    'default': 0,
                    'public': False}]
  sub_title = '{pin_id}'

  @property
  def id(self):
    return f'pin:{id(self)}'

  def execute(self):
    pass
