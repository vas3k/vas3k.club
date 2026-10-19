# Local development

The default [Docker setup](../README.md#-running-locally) starts Django, PostgreSQL, Redis, the shared queue, and webpack. It installs dependencies, applies migrations, and initializes tags. Neither Python/Node on the host nor a `.env` file is required.

## Native Python with uv

Run every command below from the repository root. Install [uv](https://docs.astral.sh/uv/getting-started/installation/), Node.js 22/npm, and PostgreSQL's `libpq` client library. uv uses `.python-version` and creates `.venv` automatically; no activation is needed.

```sh
uv sync --frozen
npm ci --prefix frontend
npm run build --prefix frontend
```

### Database and Redis

Use your own local PostgreSQL and Redis services. Create the database and configure `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT` as needed; configure Redis through `REDIS_HOST` and `REDIS_PORT`.

Django defaults to database `vas3k_club`, user `postgres`, no password, PostgreSQL at `localhost:5432`, and Redis at `localhost:6379`. These defaults do not provision services or credentials. Use PostgreSQL, not SQLite. The default Docker Compose stack does not publish database/Redis ports to the host.

### Start Django

```sh
uv run python manage.py migrate
uv run python manage.py update_tags
uv run python manage.py runserver 0.0.0.0:8000
```

In separate terminals, start the shared queue and frontend watcher when needed:

```sh
uv run python manage.py qcluster
npm run watch --prefix frontend
```

Open [the local site](http://127.0.0.1:8000/). Use `/godmode/dev_login/` for an admin or `/godmode/random_login/` for a new member; these routes only work in debug mode. Create sample content locally through the site. Production imports are not part of setup.

## Optional configuration

Settings read exported variables or an ignored `.env` file. To keep configuration between terminals, copy `club/.env.example` to `.env` at the repository root, then uncomment and fill only the settings you need. The example is commented out so copying it does not enable fake credentials. Keep only one local `.env`; an old `club/.env` is found before the root file and can hide its values.

The Docker development containers receive database/Redis settings from Compose; do not replace their service hosts with `localhost`. The root `.env` is also visible inside the bind-mounted app directory. Bot tokens, SMTP, payments, and AI credentials are optional for ordinary website development.

## Telegram bots

The Club bot and helpdeskbot are independent programs. Use separate development bots and chats. Keep `DEBUG=true` to use polling.

- Club bot: set `TELEGRAM_TOKEN`, `TELEGRAM_BOT_URL`, and `TELEGRAM_ADMIN_CHAT_ID`; configure the other Club chat/channel IDs for the features you exercise.
- Helpdeskbot: set `TELEGRAM_HELP_DESK_BOT_TOKEN`, `TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_ID`, and `TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_DISCUSSION_ID`. Link the question channel to its discussion group and give the bot access to both.

Obtain bot tokens from [BotFather](https://t.me/BotFather). Keep the shared queue running for queued notifications and long-running work.

Native commands, each in its own terminal:

```sh
uv run python bot/main.py
uv run python helpdeskbot/main.py
```

With the Docker development stack already running, use its prepared app environment without editing Compose:

```sh
docker compose exec club_app python3 bot/main.py
docker compose exec club_app python3 helpdeskbot/main.py
```

These commands start real polling processes for the configured development bots. They are not required to start the website.
