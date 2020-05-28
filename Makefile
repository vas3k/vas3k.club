# Set the default goal if no targets were specified on the command line
.DEFAULT_GOAL = run
# Makes shell non-interactive and exit on any error
.SHELLFLAGS = -ec

PROJECT_NAME=vas3k_club

run-dev:  ## Runs dev server
	pipenv run python manage.py runserver 0.0.0.0:8000

run-queue:  ## Runs task broker
	pipenv run python manage.py qcluster

run-uvicorn:  ## Runs uvicorn (ASGI) server in managed mode
	pipenv run uvicorn --fd 0 --lifespan off club.asgi:application

docker-run-dev:  ## Runs dev server in docker
	pipenv run python ./utils/wait_for_postgres.py
	pipenv run python manage.py migrate
	pipenv run python manage.py runserver 0.0.0.0:8000

docker-run-production:  ## Runs production server in docker
	python3 manage.py migrate
	uvicorn --lifespan off --host 0.0.0.0 --port 8080 club.asgi:application

help:  ## Display this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | sort \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[0;32m%-30s\033[0m %s\n", $$1, $$2}'

lint:  ## Lint code with flake8
	@pipenv run flake8 $(PROJECT_NAME)

requirements:  ## Generate requirements.txt for production
	pipenv lock --requirements > requirements.txt

migrate:  ## Migrate database to the latest version
	pipenv run python3 manage.py migrate

build-frontend:  ## Runs webpack
	npm run --prefix frontend build

test-ci: lint  ## Run tests (intended for CI usage)

.PHONY: \
  docker-run-dev \
  docker-run-production \
  run-dev \
  run-queue \
  run-uvicorn \
  requirements \
  help \
  lint \
  migrate \
  build-frontend \
  test-ci
