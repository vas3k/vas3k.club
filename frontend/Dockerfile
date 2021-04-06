FROM node:14-slim

WORKDIR /app/frontend

COPY .  ./

RUN npm ci
RUN npm run build

