FROM node:18 AS builder

WORKDIR /app
COPY ./package*.json ./
RUN npm ci
COPY . ./
RUN npm run build