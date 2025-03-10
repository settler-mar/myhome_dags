# Vue Frontend
FROM python:3.11.11 as build-stage
RUN apt-get update && apt-get install -y curl

WORKDIR /app/backend
COPY backend/ .
RUN python -m pip install uvicorn
run python -m pip install pyyaml
RUN python -m pip install -r requirements.txt
EXPOSE 3000

CMD ["uvicorn", "websrv:app", "--reload", "--host", "0.0.0.0", "--port", "3000"]