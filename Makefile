SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

PROJECT_NAME := vas3k_club

.PHONY: run-dev
run-dev:  ## Run dev server
	pipenv run python manage.py runserver 0.0.0.0:8000

.PHONY: run-queue
run-queue:  ## Run task broker
	pipenv run python manage.py qcluster

.PHONY: run-bot
run-bot:  ## Run telegram bot
	pipenv run python bot/main.py

.PHONY: run-uvicorn
run-uvicorn:  ## Run uvicorn (ASGI) server
	pipenv run uvicorn --fd 0 --lifespan off club.asgi:application

.PHONY: migrate
migrate:  ## Migrate database to the latest version
	pipenv run python3 manage.py migrate

.PHONY: psql
psql:  ## Connect to local database
	psql -h localhost -p 5433 -d $(PROJECT_NAME) -U vas3k

.PHONY: build-frontend
build-frontend:  ## Run webpack build
	npm run --prefix frontend build

.PHONY: lint
lint:  ## Lint code with flake8
	@pipenv run flake8 $(PROJECT_NAME)

.PHONY: test
test:  ## Run backend tests
	pipenv run python3 manage.py test

.PHONY: test-frontend
test-frontend:  ## Run frontend tests
	cd frontend && npm test

.PHONY: test-all
test-all: test test-frontend  ## Run all tests (backend + frontend)

.PHONY: test-ci
test-ci:  ## Run backend tests (CI)
	python3 manage.py test

.PHONY: test-frontend-ci
test-frontend-ci:  ## Run frontend tests (CI)
	cd frontend && npm run test:ci

.PHONY: docker-run-dev
docker-run-dev:  ## Run dev server in docker
	python3 ./utils/wait_for_postgres.py
	python3 manage.py migrate
	python3 manage.py update_tags
	python3 manage.py runserver 0.0.0.0:8000

.PHONY: docker-run-production
docker-run-production: docker-migrate docker-update-achievements
	cp -r /app/frontend/static /tmp/
	gunicorn club.asgi:application -w 5 -k uvicorn.workers.UvicornWorker --bind=0.0.0.0:8814 --timeout 60 --max-requests 1500 --max-requests-jitter 300 --capture-output --log-level debug --access-logfile - --error-logfile -

.PHONY: docker-run-queue
docker-run-queue:
	python3 manage.py qcluster

.PHONY: docker-run-bot
docker-run-bot:
	python3 bot/main.py

.PHONY: docker-run-helpdeskbot
docker-run-helpdeskbot:
	python3 helpdeskbot/main.py

.PHONY: docker-run-cron
docker-run-cron:
	env >> /etc/environment
	cron -f -l 2

.PHONY: docker-migrate
docker-migrate:
	python3 manage.py migrate

.PHONY: docker-update-achievements
docker-update-achievements:
	python3 manage.py update_achievements

.PHONY: help
help:  ## Display this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | sort \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[0;32m%-30s\033[0m %s\n", $$1, $$2}'
