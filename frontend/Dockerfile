FROM node:25-slim@sha256:5aea649bacdc35e8e20571131c4f3547477dfe66e677d45c005af6dbd1edfaa7

WORKDIR /app/frontend

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build
