# Set the default goal if no targets were specified on the command line
.DEFAULT_GOAL = run
# Makes shell non-interactive and exit on any error
.SHELLFLAGS = -ec

PROJECT_NAME=vas3k_club

run-dev:  ## Runs dev server
	pipenv run python manage.py runserver 0.0.0.0:8000

run-queue:  ## Runs task broker
	pipenv run python manage.py qcluster

docker-run-queue:
	python3 manage.py qcluster

run-bot:  ## Runs telegram bot
	pipenv run python bot/main.py

docker-run-bot:
	python3 bot/main.py

docker-run-helpdeskbot:
	python3 helpdeskbot/main.py

docker-run-cron:
	env >> /etc/environment
	cron -f -l 2

run-uvicorn:  ## Runs uvicorn (ASGI) server in managed mode
	pipenv run uvicorn --fd 0 --lifespan off club.asgi:application

docker-run-dev:  ## Runs dev server in docker
	python3 ./utils/wait_for_postgres.py
	python3 manage.py migrate
	python3 manage.py update_tags
	python3 manage.py runserver 0.0.0.0:8000

docker-run-production: docker-migrate docker-update-achievements
	cp -r /app/frontend/static /tmp/
	gunicorn club.asgi:application -w 7 -k uvicorn.workers.UvicornWorker --bind=0.0.0.0:8814 --capture-output --log-level debug --access-logfile - --error-logfile -

docker-update-achievements:
	python3 manage.py update_achievements

help:  ## Display this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | sort \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[0;32m%-30s\033[0m %s\n", $$1, $$2}'

lint:  ## Lint code with flake8
	@pipenv run flake8 $(PROJECT_NAME)

migrate:  ## Migrate database to the latest version
	pipenv run python3 manage.py migrate

docker-migrate:
	python3 manage.py migrate

build-frontend:  ## Runs webpack
	npm run --prefix frontend build

test:
	pipenv run python3 manage.py test

test-ci:   ## Run tests (intended for CI usage)
	python3 manage.py test

psql:
	psql -h localhost -p 5433 -d vas3k_club -U vas3k

.PHONY: \
  docker-run-dev \
  docker-run-production \
  run-dev \
  run-queue \
  run-bot \
  docker-run-bot \
  run-uvicorn \
  requirements \
  help \
  lint \
  migrate \
  build-frontend \
  test-ci
