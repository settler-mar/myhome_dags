# Vue Frontend
FROM python:3.11.11 as build-stage
RUN apt-get update && \
    apt-get install -y curl && \
    apt install -y --no-install-recommends

RUN apt install iw fontforge python3-fontforge -y

RUN apt clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
COPY backend/ .
RUN python -m pip install uvicorn pyyaml websockets
RUN python -m pip install -r requirements.txt
EXPOSE 3000

CMD ["uvicorn", "websrv:app", "--reload", "--host", "0.0.0.0", "--port", "3000"]