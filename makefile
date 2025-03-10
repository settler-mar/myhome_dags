.EXPORT_ALL_VARIABLES:

# Install dependencies
install_full:
	bash install.sh
	make install

install:
	cd backend && pip install -r requirements.txt --break-system-packages
	cd frontend && yarn install

# Run the application in development mode
run_backend:
	cd backend && uvicorn websrv:app --reload --host 0.0.0.0 --port 3000

run_frontend:
	cd frontend && yarn run serve

run_docker:
	cd docker && bash start.sh

run:
	make run_backend & make run_frontend

start:
	make run

build_frontend:
	cd frontend && yarn run build

run_prod:
	cd docker_prod && sudo docker compose up -d

stop_prod:
	cd docker_prod && sudo docker compose down