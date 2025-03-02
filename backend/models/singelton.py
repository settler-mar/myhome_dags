class SingletonClass(object):
  is_initialized = False
  instance = {}

  def __init__(self):
    if self.is_initialized:
      return
    self.is_initialized = True

  def __new__(cls, *args, **kwargs):
    # print(f'Load instance {cls.__name__}')
    if not hasattr(cls, 'instance'):
      cls.instance = {}
    if cls.__name__ not in cls.instance:
      cls.instance[cls.__name__] = super(SingletonClass, cls).__new__(cls)
      print(f'Creating new instance {cls.__name__} with id {id(cls.instance[cls.__name__])}')
    return cls.instance[cls.__name__]
