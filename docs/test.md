# Testing

## Backend

Needs **uv**, **Postgres**, **Redis**, and a built frontend (`webpack-stats.json`).

```sh
docker compose up -d postgres redis
cd frontend && npm ci && npm run build && cd ..
make test
# or: TESTS_RUN=true uv run python manage.py test
```

`make test` sets `TESTS_RUN=true` for you. If you run `manage.py test` by hand, also set:

```dotenv
TESTS_RUN=true
POSTGRES_DB=vas3k_club
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
REDIS_DB=0
REDIS_HOST=localhost
```

CI runs the same suite on every PR ([`.github/workflows/tests.yml`](../.github/workflows/tests.yml)).

Official Django testing docs: https://docs.djangoproject.com/en/6.0/topics/testing/overview/

## Frontend

Jest + jsdom. Covers utilities and DOM helpers. No Postgres/Redis/Python needed.

```sh
make test-frontend
# or: cd frontend && npm test
```

Requires Node.js 22+. CI runs this as a separate `frontend-test` job.
