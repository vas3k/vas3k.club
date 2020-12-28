FROM node:14-slim

WORKDIR /app/frontend

COPY ./package.json  ./
COPY ./package-lock.json ./

RUN npm ci

COPY ./ ./
RUN npm run build

