import asyncio

from orchestrator.dag_manager import DAGManager
from orchestrator.orchestrator import Orchestrator
import nest_asyncio

nest_asyncio.apply()


def main():
  # Инициализация базы данных
  # db_manager = DBManager()

  # Инициализация DAG менеджера
  dag_manager = DAGManager()

  # Инициализация оркестратора
  orchestrator = Orchestrator()

  first_dag = None
  pr_dag = None

  # Добавление DAG-ов в оркестратор
  asyncio.run(dag_manager.create_dag('tpl:New template1|0.0.3'))

  # for i in range(5):
  #   # Добавление DAG-ов в оркестратор
  #   dag = dag_manager.create_dag('Delay', {'delay_seconds': 3 + i})
  #   if i == 0:
  #     first_dag = dag
  #   else:
  #     pr_dag.add_output(dag)
  #   pr_dag = dag
  #
  #   for j in range(5):
  #     # Добавление узлов в DAG
  #     node = dag_manager.create_dag('Delay', {'delay_seconds': 1 + j})
  #     dag.add_output(node)

  # Запуск REST API
  # api = create_api()
  # api.run(host='0.0.0.0', port=5000)
  # orchestrator.kill()


if __name__ == "__main__":
  main()
