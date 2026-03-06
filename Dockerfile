FROM ghcr.io/astral-sh/uv:0.10.7-python3.12-trixie-slim AS python-builder

ARG MODE=dev
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

RUN apt-get update \
    && apt-get install --no-install-recommends -yq \
      build-essential \
      libgdal-dev \
      libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY Pipfile Pipfile.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /opt/venv \
    && uv pip install --python=/opt/venv/bin/python pipenv==2026.0.3 \
    && if [ "$MODE" = "production" ]; then \
        /opt/venv/bin/pipenv requirements > requirements.txt; \
    else \
        /opt/venv/bin/pipenv requirements --dev > requirements.txt; \
    fi \
    && uv pip uninstall --python=/opt/venv/bin/python pipenv \
    && uv pip install --python=/opt/venv/bin/python -r requirements.txt

FROM node:22-slim@sha256:dd9d21971ec4395903fa6143c2b9267d048ae01ca6d3ea96f16cb30df6187d94 AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.14-slim-trixie@sha256:6a27522252aef8432841f224d9baaa6e9fce07b07584154fa0b9a96603af7456

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install --no-install-recommends -yq \
      cron \
      gdal-bin \
      libpq5 \
      make \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --no-log-init --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --link --from=python-builder /opt/venv /opt/venv
COPY --link . .
COPY --link --from=frontend-builder /app/frontend/static/dist/ ./frontend/static/dist/
COPY --link --from=frontend-builder /app/frontend/webpack-stats.json ./frontend/webpack-stats.json
COPY --link --chmod=600 etc/crontab /etc/crontab

EXPOSE 8814
USER 1000:1000
