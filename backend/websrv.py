from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from orchestrator.dag_manager import router as dag_router, DAGManager
from orchestrator.orchestrator import router as orchestrator_router, Orchestrator
from orchestrator.template_manager import router as template_router, TemplateManager
from utils.socket_utils import connection_manager
from pathlib import Path
from os import path
from utils.db_utils import init_db
import nest_asyncio
from utils.auth import create_auth_route
from utils.configs import config
from utils.error_logger import add_route as error_logger_route, init_error_handling
from utils.system import add_route as system_route
from models.connections import init_connectors
from models.devices import devices_init

from utils.google_connector import GoogleConnector
# from init import init
from utils.logs import init_routes as init_logs

PORT = config['port'] or 3000

# Initialize the FastAPI app
app = FastAPI()
app.add_middleware(
  CORSMiddleware,
  allow_credentials=True,
  allow_origins=["*"],
  allow_methods=["*"],
  allow_headers=["*"],
)

print()
print("Starting FastAPI server...")
create_auth_route(app)
config.create_routes(app)
init_db(app)


def init_dags(add_routes=True):
  connectors = init_connectors(app, add_routes)
  devices_init(app, add_routes)
  connectors.start_connectors()
  Orchestrator()
  if add_routes:
    app.include_router(orchestrator_router, prefix="/api")
    app.include_router(dag_router, prefix="/api")
    app.include_router(template_router, prefix="/api")


init_dags()
init_logs(app)
error_logger_route(app)
init_error_handling()
system_route(app)


# nest_asyncio.apply()

# Add alive status route
@app.get("/api")
async def alive():
  """
  Check if the server is alive
  """
  return {"status": "alive"}


@app.get("/api/restart")
async def restart():
  """
  Restart the server
  """
  print('start restart')
  from models.singelton import SingletonClass
  SingletonClass.restart_all()
  init_dags(False)
  return {"status": "restarting", "message": "Server will restart"}


# Websocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, access_token=Cookie(None)):
  # if access_token is None:
  #   await websocket.close()
  await connection_manager.connect(websocket)
  try:
    while True:
      data = await websocket.receive_text()
      await connection_manager.broadcast(f"Message text was: {data}")
  except WebSocketDisconnect:
    connection_manager.disconnect(websocket)
    await connection_manager.broadcast("A client just disconnected.")


def join_dist():
  # Serve the Vue app in production mode
  try:
    # Directory where Vue app build output is located
    build_dir = path.realpath(path.join(path.dirname(__file__), ".."))
    if path.exists(path.join(build_dir, 'dist')):
      build_dir = path.join(build_dir, 'dist')
    elif path.exists(path.join(build_dir, 'frontend')) and path.exists(path.join(build_dir, 'frontend', 'dist')):
      build_dir = path.join(build_dir, 'frontend', 'dist')
    else:
      print('No build directory found')
      return
    print('build_dir', build_dir)
    index_path = path.join(build_dir, "index.html")

    # Serve assets files from the build directory
    app.mount("/assets", StaticFiles(directory=path.join(build_dir, "assets")), name="assets")

    # Catch-all route for SPA
    @app.get("/{catchall:path}")
    async def serve_spa(catchall: str):
      # If the requested file exists, serve it, else serve index.html
      file_path = path.join(build_dir, catchall)
      if path.exists(file_path) and path.isfile(file_path):
        return FileResponse(file_path)
      return FileResponse(index_path)

  except RuntimeError:
    # The build directory does not exist
    print("No build directory found. Running in development mode.")


GoogleConnector(False)
join_dist()

print("\nRunning FastAPI app...")
print(" - FastAPI is available at " + f"http://localhost:{PORT}/api")
print(" - Swagger UI is available at " + f"http://localhost:{PORT}/docs")
print(" - Redoc is available at " + f"http://localhost:{PORT}/redoc")
print("")
