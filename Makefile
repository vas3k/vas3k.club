SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

# --- Local development -------------------------------------------------------

.PHONY: run-dev
run-dev:  ## Run Django dev server
	uv run python manage.py runserver 0.0.0.0:8000

.PHONY: run-queue
run-queue:  ## Run django-q workers
	uv run python manage.py qcluster

.PHONY: run-bot
run-bot:  ## Run Telegram bot
	uv run python bot/main.py

.PHONY: migrate
migrate:  ## Apply database migrations
	uv run python manage.py migrate

.PHONY: build-frontend
build-frontend:  ## Build frontend assets once
	npm run --prefix frontend build

.PHONY: lint
lint:  ## Lint Python with flake8
	@uv run flake8 .

.PHONY: test
test:  ## Run backend tests
	TESTS_RUN=true uv run python manage.py test

.PHONY: test-frontend
test-frontend:  ## Run frontend tests
	cd frontend && npm test

.PHONY: test-all
test-all: test test-frontend  ## Run backend + frontend tests

# --- CI / Docker test entrypoint ---------------------------------------------

.PHONY: test-ci
test-ci:  ## Backend tests (venv already on PATH)
	TESTS_RUN=true python manage.py test

# --- Docker Compose entrypoints ----------------------------------------------

.PHONY: docker-run-dev
docker-run-dev:  ## Dev app container
	python3 ./utils/wait_for_postgres.py
	python3 manage.py migrate
	python3 manage.py update_tags
	python3 manage.py runserver 0.0.0.0:8000

.PHONY: docker-run-production
docker-run-production:  ## Production gunicorn (WSGI)
	python3 manage.py migrate
	python3 manage.py update_achievements
	cp -r /app/frontend/static /tmp/
	gunicorn club.wsgi:application \
		-w 5 -k gthread --threads 2 \
		--bind=0.0.0.0:8814 \
		--timeout 60 \
		--max-requests 1500 --max-requests-jitter 300 \
		--capture-output --log-level info \
		--access-logfile - --error-logfile -

.PHONY: docker-run-queue
docker-run-queue:  ## Queue workers container
	python3 manage.py qcluster

.PHONY: docker-run-bot
docker-run-bot:  ## Club Telegram bot container
	python3 bot/main.py

.PHONY: docker-run-helpdeskbot
docker-run-helpdeskbot:  ## Helpdesk bot container
	python3 helpdeskbot/main.py

.PHONY: docker-run-cron
docker-run-cron:  ## Cron container
	exec supercronic -json -split-logs -sentry-dsn="$$SENTRY_DSN" /app/etc/crontab

.PHONY: help
help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | sort \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[0;32m%-28s\033[0m %s\n", $$1, $$2}'
