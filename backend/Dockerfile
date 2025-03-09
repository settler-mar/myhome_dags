FROM python:3.12
RUN apt-get update

WORKDIR /backend
COPY . ./
RUN pip3 install --no-cache-dir --upgrade -r requirements.txt

EXPOSE 3000

CMD ["uvicorn", "websrv:app", "--host", "