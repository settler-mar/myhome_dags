FROM node:20 as build-stage
RUN apt-get update

RUN apt-get install -y apt-transport-https ca-certificates
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list
RUN apt-get install -y yarn

WORKDIR /frontend
COPY . ./
RUN yarn install

EXPOSE 8080

CMD [ "npm", "run", "serve" ]