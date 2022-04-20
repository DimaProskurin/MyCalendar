# syntax=docker/dockerfile:1
FROM python:3.8

RUN python3.8 -m pip install --upgrade pip && \
    python3.8 -m pip install poetry

COPY . /app
WORKDIR /app
RUN poetry install
