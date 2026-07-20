FROM ghcr.io/astral-sh/uv:0.10.12-python3.14-trixie-slim AS python-builder

ARG MODE=dev
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

RUN apt-get update \
    && apt-get install --no-install-recommends -yq \
      build-essential \
      libgdal-dev \
      libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$MODE" = "production" ]; then \
        uv sync --frozen --no-dev --no-install-project; \
    else \
        uv sync --frozen --no-install-project; \
    fi

FROM node:22-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383 AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.14-slim-trixie@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6

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
      libxml2 \
      libxslt1.1 \
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
