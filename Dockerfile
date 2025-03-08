# Vue Frontend
FROM node:20 as build-stage
WORKDIR /frontend
COPY frontend/ .
RUN npm install -g yarn
RUN yarn install
RUN npm run build

# Python Backend
FROM python:3.12
WORKDIR /backend
COPY backend/ .
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY --from=build-stage /frontend/dist dist
CMD ["uvicorn", "websrv:app", "--host", "0.0.0.0", "--port", "3000"]