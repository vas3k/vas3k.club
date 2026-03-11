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

FROM python:3.12-slim-trixie@sha256:39e4e1ccb01578e3c86f7a0cf7b7fd89b8dbe2c27a88de11cf726ba669469f49

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

ARG SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.43/supercronic-linux-amd64
ARG SUPERCRONIC_SHA1SUM=f97b92132b61a8f827c3faf67106dc0e4467ccf2

RUN apt-get update \
    && apt-get install --no-install-recommends -yq \
      curl \
      gdal-bin \
      libpq5 \
      make \
    && curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  supercronic-linux-amd64" | sha1sum -c - \
    && chmod +x supercronic-linux-amd64 \
    && mv supercronic-linux-amd64 /usr/local/bin/supercronic \
    && apt-get purge -yq curl \
    && apt-get autoremove -yq \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --no-log-init --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --link --from=python-builder /opt/venv /opt/venv
COPY --link . .
COPY --link --from=frontend-builder /app/frontend/static/dist/ ./frontend/static/dist/
COPY --link --from=frontend-builder /app/frontend/webpack-stats.json ./frontend/webpack-stats.json
COPY --link etc/crontab /app/etc/crontab
RUN supercronic -test /app/etc/crontab

EXPOSE 8814
USER 1000:1000
