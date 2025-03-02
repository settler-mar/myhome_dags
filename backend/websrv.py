from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from orchestrator.dag_manager import router as dag_router, DAGManager
from orchestrator.orchestrator import router as orchestrator_router, Orchestrator
from orchestrator.template_manager import router as template_router, TemplateManager
from utils.socket_utils import connection_manager
from pathlib import Path
from utils.db_utils import init_db
import nest_asyncio
from utils.auth import create_auth_route
from utils.configs import config
from models.connections import init_connectors
from models.devices import devices_init

nest_asyncio.apply()

# from init import init

PORT = 3000

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
connectors = init_connectors(app)
devices_init(app)
connectors.start_connectors()


# Add alive status route
@app.get("/api")
async def alive():
  """
  Check if the server is alive
  """
  return {"status": "alive"}


Orchestrator()
app.include_router(orchestrator_router, prefix="/api")
app.include_router(dag_router, prefix="/api")
app.include_router(template_router, prefix="/api")


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


# dags

# Serve the Vue app in production mode
try:
  # Directory where Vue app build output is located
  build_dir = Path(__file__).resolve().parent / "dist"
  index_path = build_dir / "index.html"

  # Serve assets files from the build directory
  app.mount("/assets", StaticFiles(directory=build_dir / "assets"), name="assets")


  # Catch-all route for SPA
  @app.get("/{catchall:path}")
  async def serve_spa(catchall: str):
    # If the requested file exists, serve it, else serve index.html
    path = build_dir / catchall
    if path.is_file():
      return FileResponse(path)
    return FileResponse(index_path)

except RuntimeError:
  # The build directory does not exist
  print("No build directory found. Running in development mode.")

# Initialize the app
# init()

print("\nRunning FastAPI app...")
print(" - FastAPI is available at " + f"http://localhost:{PORT}/api")
print(" - Swagger UI is available at " + f"http://localhost:{PORT}/docs")
print(" - Redoc is available at " + f"http://localhost:{PORT}/redoc")
print("")
