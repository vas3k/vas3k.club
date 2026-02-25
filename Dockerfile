FROM python:3.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c AS builder

ARG MODE=dev
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install --no-install-recommends -yq \
      build-essential libgdal-dev libpq-dev npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY Pipfile Pipfile.lock ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install pipenv==2026.0.3 \
    && if [ "$MODE" = "production" ]; then \
        /opt/venv/bin/pipenv requirements --keep-outdated > requirements.txt; \
    else \
        /opt/venv/bin/pipenv requirements --dev > requirements.txt; \
    fi \
    && /opt/venv/bin/pip install -r requirements.txt

COPY frontend/package.json frontend/package-lock.json ./frontend/
WORKDIR /app/frontend
RUN npm ci
COPY frontend/ /app/frontend/
RUN npm run build

FROM python:3.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install --no-install-recommends -yq \
      cron gdal-bin libpq5 make \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --link --from=builder /opt/venv /opt/venv
COPY --link . .
COPY --link --from=builder /app/frontend/static/dist/ ./frontend/static/dist/
COPY --link --from=builder /app/frontend/webpack-stats.json ./frontend/webpack-stats.json
COPY --link --chmod=600 etc/crontab /etc/crontab

USER 1000:1000
