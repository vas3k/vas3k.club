FROM node:14-slim

WORKDIR /app/frontend

COPY ./frontend/package.json  ./
COPY ./frontend/package-lock.json ./

RUN npm ci

COPY ./frontend ./
RUN npm run build

