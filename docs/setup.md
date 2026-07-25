# Advanced setup

For most contributors, `docker compose up` from the [README](../README.md) is enough. Use this guide when you want to run parts of the stack natively, enable bots, or seed local data.

## Native local development

### 1. Python (uv)

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. `uv sync`
3. Check it works: `uv run python -c "import django; print(django.get_version())"`

Requires **Python 3.14+** (see `pyproject.toml`).

### 2. Postgres and Redis

Easiest: start only the infra containers:

```sh
docker compose up -d postgres redis
```

Connection defaults (also used by Django when env vars are unset):

```dotenv
POSTGRES_DB=vas3k_club
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
REDIS_HOST=localhost
REDIS_DB=0
```

### 3. Frontend

Needs **Node.js 22+**.

```sh
cd frontend
npm run watch   # runs npm ci first, then webpack --watch
```

Or a one-shot build: `make build-frontend`.

### 4. Run the app

```sh
make migrate
make run-queue   # in one terminal
make run-dev     # in another → http://127.0.0.1:8000/
```

Same thing without make:

```sh
uv run python manage.py migrate
uv run python manage.py qcluster
uv run python manage.py runserver 0.0.0.0:8000
```

Dev login shortcuts still work: `/godmode/dev_login/` and `/godmode/random_login/` (only when `DEBUG=true`).

## Telegram bot / helpdesk bot

1. `cp ./club/.env.example ./club/.env`
2. Fill the Telegram-related fields (`TELEGRAM_TOKEN`, chat/channel IDs, etc.)
   - Token: [@BotFather](https://t.me/BotFather)
   - Chat/channel IDs: forward a message to [@JsonDumpBot](https://t.me/JsonDumpBot) or [@getidsbot](https://t.me/getidsbot)
3. Uncomment the `bot` / `helpdeskbot` services in `docker-compose.yml`, then:

```sh
docker compose up --build
```

Or run natively: `make run-bot`.

## Import posts from production into a local DB

`import_posts_to_dev` pulls public posts from https://vas3k.club/feed.json:

```sh
uv run python manage.py import_posts_to_dev
uv run python manage.py import_posts_to_dev --pages 10
uv run python manage.py import_posts_to_dev --pages 10 --skip 5 --force

# inside docker
docker exec -it club_app python3 manage.py import_posts_to_dev --pages 2
```

Private posts and comments need a [service app token](https://vas3k.club/apps/create/):

```sh
uv run python manage.py import_posts_to_dev --with-comments --service-token XXX
uv run python manage.py import_posts_to_dev --with-private --with-comments --service-token XXX
```

## Infrastructure reference

See [docker-compose.yml](../docker-compose.yml) for the full local stack.
