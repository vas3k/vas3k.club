<div align="center">
  <br>
  <img src="frontend/static/images/logo/logo-256.png" alt="">
  <h1>vas3k.club</h1>
</div>

Welcome to the [vas3k.club](https://vas3k.club) codebase. We're building our own little IT-lifestyle community. We've opensourced the code so that every member could contribute or implement a feature that they want.

[vas3k.club](https://vas3k.club) is a platform with private and paid memberships that has emerged around the [vas3k.blog](https://vas3k.blog) blog and satellite chat rooms. It's not a typical IT community with tutorials and framework reviews, but rather more of a lifestyle one. We are trying to build a peaceful and useful ecosystem, which the Internet has lost a long ago. Therefore, we carefully select and filter new members and do not seek wild growth.

Our values: honesty, fair share, respect for other members, rationality, friendliness and usefulness. We have a zero-tolerance policy on anonymity, insults and toxicity. But we always try to stay in touch with reality, so we're also not tolerant of witch hunting and call-out culture.

We're a bullshitless community!

## 🛠 Architecture

Django renders pages and handles routing, authentication, forms, and JSON endpoints. React islands add interactive pieces inside those pages using plain JavaScript and JSX. Vite builds the frontend, and django-vite inserts either development-server URLs or hashed production assets into the templates. There is no SPA or client-side router.

| Part | Responsibility |
| --- | --- |
| Django + PostgreSQL | Pages, APIs, membership, posts, comments, and other persistent data |
| React islands + Vite | Interactive widgets; EasyMDE editors and Mapbox maps |
| Redis + Django Q2 | Cache and queued background work, including notifications |
| Club bot and helpdeskbot | Separate Telegram services sharing the Django code and database |
| Supercronic | Scheduled Django management commands from `etc/crontab` |

Templates live in `templates/`, JavaScript in `frontend/src/`, and styles/images/fonts in `frontend/static/`. See [Frontend](#frontend) for adding islands and working with assets.

## 🔮 Running locally

Choose Docker for a complete development environment, or native tools if you already run PostgreSQL and Redis locally. Run commands from the repository root.

### Docker: simplest setup

Install Docker with Compose, then:

```sh
git clone https://github.com/vas3k/vas3k.club.git
cd vas3k.club
docker compose up --build
```

On Apple Silicon or another ARM host, use `DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose up --build` because the image currently includes an amd64 Supercronic binary.

Compose starts Django, PostgreSQL, Redis, queue workers, and Vite. It installs dependencies, applies migrations, and initializes tags. No local Python/Node installation or `.env` is needed. Wait for startup, then open [localhost:8000](http://127.0.0.1:8000/).

Python changes reload automatically; Vite handles frontend changes on port 5173. Rebuild after changing Python dependencies or the Dockerfile. Use `docker compose logs -f club_app vite` to inspect startup problems and `docker compose stop` to stop the stack while retaining its containers. This development configuration does not declare a named PostgreSQL volume; do not treat it as durable storage for important data.

### Native: uv + Node

Install **uv**, **Node.js 22/npm**, **PostgreSQL** (including the `libpq` client library), and **Redis**. Start the database services and create a local database. Django defaults to database `vas3k_club`, user `postgres`, no password, and services on `localhost:5432` and `localhost:6379`. Set `POSTGRES_*` and `REDIS_*` variables if your setup differs; [club/.env.example](club/.env.example) lists them. The default Compose database ports are not exposed to host processes.

Install and initialize once:

```sh
uv sync --frozen
npm ci --prefix frontend
npm run build --prefix frontend
uv run python manage.py migrate
uv run python manage.py update_tags
```

Start Django and Vite in separate terminals:

```sh
# Terminal 1
VITE_DEV_MODE=true uv run python manage.py runserver

# Terminal 2
npm run dev --prefix frontend
```

Open [localhost:8000](http://127.0.0.1:8000/). Run `uv run python manage.py qcluster` in another terminal when you need background jobs.

Without a Vite server, omit `VITE_DEV_MODE=true` and use `npm run build --prefix frontend` after frontend edits. Restart Django after each build to refresh its cached manifest. If port 5173 is busy, prefix **both** development commands with `VITE_DEV_SERVER_PORT=5174`.

### Sign in and configure optional services

- [Admin login](http://127.0.0.1:8000/godmode/dev_login/) creates or reuses the `dev` account; a newly created account has the `god` role.
- [Random member login](http://127.0.0.1:8000/godmode/random_login/) creates a new member each time.
- [Godmode](http://127.0.0.1:8000/godmode/) is the administration UI.

These login shortcuts require debug/test mode. Use local sample data. Telegram, SMTP, payment, and AI credentials are optional for basic website work; some features, including creating posts, require a linked development bot. Configure optional services as described below. Image uploads currently target the live image service by default; configure a non-production upload service before testing uploads.

## ☄️ Checks

With native dependencies and local database services ready:

```sh
TESTS_RUN=true uv run python manage.py test
npm test --prefix frontend
npm run build --prefix frontend
```

For backend tests in the running Docker stack:

```sh
docker compose exec -e TESTS_RUN=true club_app python3 manage.py test
```

Append an app's test module, such as `payments.tests`, for a focused backend run. Tests require local PostgreSQL with permission to create test databases, Redis, and built frontend assets; external services are mocked.

[CI](.github/workflows/tests.yml) runs backend tests, existing frontend tests, and Flake8. Fatal Python lint errors block CI; other lint findings are reported as warnings. The [Compose build check](.github/workflows/check_build_and_run.yml) also verifies development-stack startup and frontend compilation on pull requests.

## Frontend

The frontend is a collection of React islands inside server-rendered Django pages. Vite handles JSX, CSS imports, asset hashing, and development reloads. Vitest uses the same pipeline for tests. There is no client-side router or separate frontend server in production.

| Location | Purpose |
| --- | --- |
| `templates/` | Django pages, includes, email and Markdown notification templates |
| `frontend/src/islands/` | Lazily mounted React components |
| `frontend/src/components/`, `hooks/`, `lib/` | Shared UI, hooks, and browser integrations |
| `frontend/static/` | CSS, images, fonts, and generated `dist/` assets |

To add an island, create a default-exported component in `frontend/src/islands/`, then render it in a template:

```django
{% load islands %}
{% island "ThemeSwitcher" %}
```

Pass initial values and named URLs as tag arguments. The tag safely serializes JSON and converts `snake_case` argument names to `camelCase` props. Django still owns form submission and validation. JSON endpoints use domain URLs ending in `.json` and the shared `ClubApi` client.

Keep UI state local. Use effects for external integrations and clean them up on unmount. Comment and reply editors use EasyMDE on desktop and native textareas on phones or narrow layouts, with mention suggestions in both. Full post editors continue to use EasyMDE. Mapbox owns map rendering and markers. Styles use the existing design tokens and 570px mobile breakpoint. Check desktop and narrow layouts, touch targets, IME input, light/dark/system themes, and real-phone keyboard behavior when changing these components.

### Optional configuration and bots

Copy `club/.env.example` to a root `.env` and uncomment only settings you need. Keep one local configuration file: an old `club/.env` can take precedence. Never commit credentials. Compose sets its own database/Redis service hosts; do not replace those with `localhost` inside containers.

Use separate development bots and chats. The Club bot needs `TELEGRAM_TOKEN`, `TELEGRAM_BOT_URL`, and the relevant chat IDs. Helpdesk needs `TELEGRAM_HELP_DESK_BOT_TOKEN`, `TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_ID`, and `TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_DISCUSSION_ID`; link its channel to the discussion group. In debug mode bots poll; production uses webhooks. Run the shared queue for notifications.

```sh
uv run python bot/main.py
# Separate terminal, if needed:
uv run python helpdeskbot/main.py
```

With Docker, run the equivalent command through `docker compose exec club_app python3 …`.

### Maintaining a club

Godmode at `/godmode/` manages rooms, moderation, member roles, and achievements. Permissions differ between curators, moderators, and administrators. Built-in tags, labels, and achievements live in `common/data/`; run `update_tags` or `update_achievements` after changing the corresponding definitions. Collectible tags are attached through the post editor. Keep backups of PostgreSQL and uploaded media and verify restores before relying on them.

## 🚢 Deployment

Production uses Docker Compose on one host, with Nginx and PostgreSQL managed outside Compose. There is no production Vite server or separate frontend runtime.

```text
Browser → Nginx → Gunicorn/Django :8814 → host PostgreSQL
              ├→ static files             Redis ← queue workers
              └→ bot webhooks :8816/:8817

One release image: web + queue + Club bot + helpdeskbot + cron
```

The [Dockerfile](Dockerfile) installs locked Python dependencies with uv and builds frontend assets with Node/Vite. The runtime image contains both Django and `frontend/static/dist/`, including the Vite manifest. [Production Compose](docker-compose.production.yml) runs each process as a separate service using that same image. The web entrypoint applies migrations, updates achievements, copies static files to the host-mounted directory, and starts Gunicorn. [Nginx](etc/nginx/vas3k.club.conf) serves `/static/` from that directory and proxies website and bot requests. Uploads use a separate image service.

### One-time host setup

1. Prepare a Linux host with Docker Compose, Nginx/TLS, and PostgreSQL. Provision the database/user and backups. Production Compose expects PostgreSQL through `host.docker.internal`; it does not create the database server.
2. Configure Nginx using [etc/nginx/vas3k.club.conf](etc/nginx/vas3k.club.conf) as a reference. Match the domain, certificate paths, static directory, and webhook routes to your host.
3. Prepare the deployment directory, currently `/home/vas3k/vas3k.club`, and an SSH account with Docker and directory access. The workflow creates `gdpr/downloads` owned by UID/GID 1000. Keep this directory and the database persistent.
4. Configure GitHub Actions secrets: `TOKEN` for GHCR access; `PRODUCTION_SSH_HOST`, `PRODUCTION_SSH_USERNAME`, and `PRODUCTION_SSH_KEY` for deployment; `SECRET_KEY` and `POSTGRES_PASSWORD`; and the integration credentials listed in the deploy workflow's **Make envfile** step. That list is the source of truth for values sent to the host.

For a fork, align the registry namespace, host paths, domains, bot routes, and integration settings in the workflow, Compose, and Nginx configuration. The workflow currently builds `ghcr.io/${github.repository_owner}/club`, while Compose reads `ghcr.io/vas3k/club`; these must resolve to the same registry repository. Compose's explicit `environment` values take precedence over `.env`, including its production host setting.

### Release steps

1. Review the change and confirm CI passes: Python lint/backend tests, frontend tests, development Compose startup, and production image build/Django checks. For frontend releases, check maps, normal/battle replies, editor uploads/mentions, and theme controls on desktop and mobile. A resized desktop browser does not verify a phone keyboard. Back up the database before migrations and record the previous image tag.
2. Merge to `master`, or manually run **Deploy production** for the intended revision. This is the production action: the [workflow](.github/workflows/deploy.yml) runs tests, builds the image, and publishes `latest` plus `sha-<seven-character-commit>` tags to GHCR.
3. The workflow pulls the exact image, generates a permission-restricted `.env` preserving literal secrets (including multiline keys), copies it and the production Compose file over SSH, validates Compose, and runs `docker compose -f docker-compose.production.yml --env-file=.env up -d`. Migrations and static-file copying happen when the web container starts.
4. Check Actions output, container status/logs, the homepage and its assets, queue processing, and bot webhooks. The workflow does not perform a complete post-deploy health check or automatic rollback; successful SSH execution alone does not prove the application is healthy.

To roll back, an operator can set `GITHUB_SHA` in the host `.env` to a retained previous image tag and rerun production Compose. Confirm database compatibility first: changing the image does not reverse migrations, and rolling forward may be safer for schema changes. The workflow prunes unused local images older than 72 hours, so a rollback may need to pull its tag from GHCR.

### Release boundaries

Check the map, profile location picker, normal/battle replies, mentions, uploads, and theme controls before release. Resizing a desktop browser is useful but does not verify iOS Safari or Android keyboards. Use a non-production image service for upload checks; `MEDIA_UPLOAD_URL` currently lives in `club/settings.py`. Payment checks need sandbox credentials. Checkout uses the URL returned by the server-created Stripe session, with no browser SDK.

The backend Stripe SDK is intentionally pinned until its API-version migration is tested. PostgreSQL/Redis major upgrades need a separate backup/restore plan. Clickers retain their original schema migration and have no Godmode administration; the existing model metadata differs in ordering and related name, so `makemigrations --check` reports that known difference. Do not generate an unrelated clicker migration during frontend work.

## 🛤 Forking and tweaking

Forks are welcome. We're small and our engine is not universal like Wordpress, but with sufficient programming skills (and using grep), you can launch your own Club website in a couple of weeks.

Three huge requests for everyone:

- Please give kudos to the original authors. "Works on vas3k.club engine" in the footer of your site will be enough.
- Please share new features you implement with us, so other folks can also benefit from them, and your own codebase minimally diverges from the original one (so you can sync updates and security fixes). Use our [feature-flags](club/features.py).
- Do not use our "issues" and chats as a support desk for your own fork.

> ♥️ [Feature-flags](club/features.py) are great. Use them to tweak your fork. Create new flags to upstream your new features or disable existing ones.

For a fork, configure your domain, mail delivery, image upload service, payment providers, bot accounts, and backups before accepting members. Customize the landing page and `templates/docs/`; use Godmode to manage rooms and member roles.

## 🙋‍♂️ How to report a bug or propose a feature?

- Open [a new issue](https://github.com/vas3k/vas3k.club/issues/new) using one of the existing templates.
- Please **use the search function** to make sure you aren't creating a duplicate.
- Provide ALL the details, screenshots, logs, etc. Bug reports without steps to reproduce will be closed.

## 😍 Contributions

Important information for everyone willing to contribute to this project.

- AI-generated PRs are NOT welcome.
- Low-effort PRs are NOT welcome.
- No cowboy PRs without prior discussion AND approval from maintainers.
- 1 PR = 1 feature. No PRs with bulk changes.
- Any PR longer than 10 lines of code must include a detailed text explanation of all changes.

**A good way to contribute bug fixes:** search the Issues to make sure the bug hasn't been reported yet. Open a new Issue with a detailed description and steps to reproduce. Open a PR with the fix (if you can), then the contributors will either merge your PR or you'll carry on the discussion in the comments.

**For new features:** open a new Issue describing the new feature you're interested in. Wait for the contributors to get back to you and give you the green light for implementation. If the contributors don't reply, it means the feature isn't of interest at the moment. ONLY after that should you open a PR for that feature.

The main point of interaction is the [Issues page](https://github.com/vas3k/vas3k.club/issues) and our [Dev-chat in Telegram](https://t.me/vas3k_club_dev). DO NOT DISCUSS FORKS THERE.

If you want to contribute but don't know where to start — come to the chat and just ask!

> The official development language at the moment is Russian, because 100% of our users speak it. We don't want to introduce unnecessary barriers for them. But we are used to writing commits and comments in English and we won't mind communicating with you in it.

## 🔐 Security and vulnerabilities

If you think you've found a critical vulnerability that should not be exposed to the public yet, you can always email me directly on Telegram [@vas3k](https://t.me/vas3k) or by email: [me@vas3k.ru](mailto:me@vas3k.ru).

Please do not test vulnerabilities in public. If you start spamming the website with "test-test-test" posts or comments, our moderators will ban you even if you had good intentions.

## 👩‍💼 License

[MIT](LICENSE)

You can use the code for your own private or commercial purposes with an author attribution (by including the original license file and mentioning vas3k.club somewhere on your website 🎩).

Feel free to contact us via email [club@vas3k.club](mailto:club@vas3k.club).

❤️
