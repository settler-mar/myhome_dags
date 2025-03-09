# Vue Frontend
FROM node:20 as build-stage
RUN apt-get update

# node and yarn
RUN apt-get install -y apt-transport-https ca-certificates
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list
RUN apt-get install -y yarn

# Python
RUN apt-get update -y \
    && apt-get upgrade -y \
    && apt-get -y install build-essential \
        zlib1g-dev \
        libncurses5-dev \
        libgdbm-dev \
        libnss3-dev \
        libssl-dev \
        libreadline-dev \
        libffi-dev \
        libsqlite3-dev \
        libbz2-dev \
        wget \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get purge -y imagemagick imagemagick-6-common

RUN cd /usr/src \
    && wget https://www.python.org/ftp/python/3.11.11/Python-3.11.11.tgz \
    && tar -xzf Python-3.11.11.tgz \
    && cd Python-3.11.11 \
    && ./configure --enable-optimizations \
    && make altinstall
RUN update-alternatives --install /usr/bin/python python /usr/local/bin/python3.11 1

WORKDIR /app/frontend
COPY ./frontend ./
RUN yarn install
EXPOSE 8080

WORKDIR /app/backend
COPY backend/ .
RUN python -m pip install uvicorn
run python -m pip install pyyaml
RUN python -m pip install -r requirements.txt
EXPOSE 3000

WORKDIR /app
COPY ./makefile ./makefile

CMD ["make", "run"]