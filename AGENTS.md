# vas3k.club contributor guidelines

These instructions apply throughout the repository. Preserve the Django site, React islands, and homegrown CSS design system. Favor small, readable changes and reuse existing code and UI.

## Working rules

- Read `git status`, relevant code, and its callers before editing. Preserve unrelated work; avoid opportunistic refactors, formatting sweeps, and dependency upgrades.
- Keep logic in its owning domain app and reuse existing dependencies; do not introduce service/repository layers for a local feature.
- Keep code explicit, with blank lines between semantic steps. Follow Flake8 style for Python. Add a newline before if, for, and any other blocks except they are following the same blocks on the upper line (like nested for loops or if's). Do not hard-wrap Markdown paragraphs.
- Never comment on simple code or what a change did. Add comments only to explain a whole function’s purpose or unintuitive behavior that future reviewers must understand to avoid mistakes; do not narrate the implementation.
- Extract utility helpers only with **3+ real call sites and 5+ meaningful lines**; inline everything else, including single-use helpers under 10 meaningful lines. Do not pad code or invent callers to qualify. Keep helpers used within one file there; put shared Python helpers in the owning app's `helpers.py` or existing shared module. Framework entry points such as views, form cleaners, and command handlers are not utility extractions.
- Never introduce leading-underscore names for functions, methods, variables, or attributes. All names must explain their purpose; do not disguise helpers as magic methods.
- Do not commit, push, or send real messages without authorization. **Never connect to or operate on production.**
- Do not add every change you made to README.md or AGENTS.md. Only change them if facts were changed or if directly requested.

## Code map

| Area | Entry points and ownership |
| --- | --- |
| Django + PostgreSQL | `club/settings.py`, `club/urls.py`; domain apps own models, forms, views, APIs, and migrations |
| Shared Python | `common/` for request, Markdown, image, and form behavior; `utils/` for existing general utilities |
| Frontend | Django templates in `templates/`; JavaScript in `frontend/src/`; styles in `frontend/static/css/`; images/fonts in `frontend/static/images/` and `frontend/static/webfonts/` |
| Club Telegram bot | `bot/main.py`, `bot/handlers/`: account linking, replies, votes, moderation, and AI assistance from `ai/` |
| Helpdesk Telegram bot | `helpdeskbot/main.py`, `helpdeskbot/handlers/`, `helpdeskbot/models.py`, `helpdeskbot/config.py`; templates in `helpdeskbot/templates/messages/` |
| Shared queue service | Redis + Django Q2 (`django_q`); `Q_CLUSTER` in `club/settings.py` |
| Manual and periodic operations | `<app>/management/commands/`; periodic schedules in `etc/crontab` |
| Administration | Custom Godmode: `godmode/config.py`, `godmode/admin.py`, `godmode/actions/`, `godmode/pages/`, and `templates/godmode/` |

## Fresh checkout and local commands

Run from the repository root. A fresh clone has no `.venv`, `.env`, installed frontend dependencies, generated bundles, or database. Use **uv** for native Python work: `uv sync --frozen` creates `.venv` automatically and `uv run` uses it without manual activation. Python is pinned by `.python-version` (currently 3.14); do not rely on the system Python or a contributor's existing setup.

Native development requires uv, Node.js 22/npm, PostgreSQL with its `libpq` client library, and Redis. Create a local database and configure access through `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT`; configure Redis through `REDIS_HOST`/`REDIS_PORT`. Defaults are database `vas3k_club`, user `postgres`, no password, PostgreSQL at `localhost:5432`, and Redis at `localhost:6379`; these defaults do not provision services or credentials. Keep PostgreSQL, not a SQLite substitute.

Export environment variables in the shell or put them in an optional ignored `.env` at the repository root, read by `club/settings.py` through `python-dotenv`; uv does not create it. `club/.env.example` is a commented reference: uncomment and fill only the settings you need; leave unused credentials unset. Bot commands require development tokens and chat IDs; bots are optional for website work.

For the first native run, install dependencies, build the frontend, apply local migrations, initialize tags, then start Django, in the order below. Start the queue and Vite dev server in separate terminals when needed.

| Task | Command |
| --- | --- |
| Install dependencies | `uv sync --frozen` and `npm ci --prefix frontend` |
| Frontend build | `npm run build --prefix frontend` |
| Apply local migrations | `uv run python manage.py migrate` |
| Initialize/update built-in tags | `uv run python manage.py update_tags` |
| Django | `uv run python manage.py runserver 0.0.0.0:8000` |
| Queue workers | `uv run python manage.py qcluster` |
| Club bot | `uv run python bot/main.py` |
| Helpdesk bot | `uv run python helpdeskbot/main.py` |
| Vite development | `npm run dev --prefix frontend`; Django uses Vite automatically when `DEBUG` is enabled outside tests |
| Generate migrations after model changes | `uv run python manage.py makemigrations <app>` |

Alternatively, use the complete development stack with `docker compose up --build --pull always`: it supplies the runtimes, PostgreSQL, Redis, queue, and Vite, and applies migrations at startup. The Dockerfile currently downloads an amd64 Supercronic binary; ARM hosts need `DOCKER_DEFAULT_PLATFORM=linux/amd64` for this image. Inside its prepared app container, run `docker compose exec club_app python3 manage.py <command>`. Compose does not publish PostgreSQL/Redis ports to the host; native uv commands need their own reachable services. Preserve both development paths.

Keep dependency declarations and locks consistent: `pyproject.toml`/`uv.lock`, `frontend/package.json`/`package-lock.json`.

## Django and business logic

- Prefer ordinary function views, Django forms, model methods, and ORM queries in the existing app. Routes live in `club/urls.py`; use named URLs and `reverse()`/`{% url %}`. Group JSON routes with their corresponding page/domain routes. Use resource URLs ending in `.json`, without a separate API prefix; a matching HTML view is not required. Use plural collection names. Keep normal POST actions that redirect in views.
- Authentication is custom: `request.me`, `request.my_session`, `users.User`, and `authn` decorators. Use `require_auth`/role decorators and `@api(...)` as appropriate; do not assume Django's `request.user` or `login_required` works here. Keep errors compatible with `club/exceptions.py` and the existing API response shapes.
- Enforce permissions, membership, moderation, rate limits, and HTTP methods on the server. Reuse visibility/query helpers, but also preserve caller-specific checks for public content, drafts, room-only posts, mutes, and private profiles. A visibility helper alone does not enforce every access rule.
- Prefer `ModelForm` for model edits. Declare inputs and their labels/widgets explicitly; keep `Meta` focused on model/fields. Use `clean_<field>()` for individual validation, `clean()` with `super()` for cross-field checks, and keep initialization separate from validation and saving.
- Include migrations with every model-state/schema change, including constraints, indexes, and relevant history models. Generate files with Django's `makemigrations` command above; use `--empty` for data migrations, then fill in the operations. Review and fix generated operations, dependencies, and data handling. Never write migration files from scratch; resolve generation problems or report the blocker. Applying migrations needs no authorization after confirming the database is local.
- **Migration == Godmode change.** Every model change or migration must include the corresponding Godmode admin update in the same patch. Update registrations, list/edit forms, hidden/editable fields, and role restrictions so the admin reflects the model; inspection alone is insufficient.
- Always use `id` for model primary keys and `<relation>_id` for foreign-key values: `user.id`, `filter(id=user.id)`, `author_id=user.id`. Never use `.pk`, `pk=`/`__pk` lookups, or `"pk"` in ORM field expressions.
- Preserve the existing naive UTC convention (`USE_TZ = False`); do not mix aware and naive datetimes or change timezone policy incidentally.
- Trace side effects across web views, APIs, bots, and admin actions. Post/comment changes can require clearing cached `html`, updating `SearchIndex`, linked posts, counters, unread state, subscriptions, and notifications. Reuse domain methods; bulk updates/deletes can bypass custom save/soft-delete behavior and history.
- Keep queries bounded and reuse `select_related`, `prefetch_related`, annotations, and pagination. Preserve `F()` counter updates, transactions, uniqueness, and duplicate-delivery safeguards for votes, payments, invites, and webhooks.
- Reuse `common/markdown/`, image-upload helpers, and URL safety checks. Keep private data out of public serializers, browser props, and logs.

## React islands and Django templates

- Django owns pages, routes, forms, and initial data. Use plain JavaScript/JSX React islands for interaction. No SPA, TypeScript, client router, or global store. Some interactive and complex UI components use Headless UI; style it with our CSS, without Tailwind or a visual UI framework. Native controls and small inline handlers are welcome.
- Keep CSS in `frontend/static/css/` and images in `frontend/static/images/`; never put stylesheets or images in `frontend/src/`.
- All React components live in `frontend/src/components/`; browser helpers live in `lib/`. An island is a component mounted independently into a Django page, not a separate component type. `core/islands.js` lazily mounts each island. Use function components for new UI; isolate imperative Mapbox/EasyMDE lifecycles. Never rewrite working map algorithms just to change syntax.
- Effects synchronize external systems; derive values during render and handle user actions in event handlers. Clean up maps, editors, timers, object URLs, listeners, and stale requests. Extract shared hooks only when the helper rules above are met. Do not mirror props in state unless they are explicitly initial values.
- Pass props with `{% load react %}` and `{% react "Component" prop_name=value %}`. The tag escapes JSON and converts snake_case to camelCase. Preserve named form inputs, template escaping, and normal POST/redirect behavior. Use `{% static %}` for ordinary assets and named domain URLs ending in `.json` for JSON calls through `ClubApi`.
- Vite and django-vite connect `src/main.js`, `static/css/index.css`, and the template asset tags. Edit source, never `frontend/static/dist/`. Use Vite's native JSX pipeline and Vitest; do not introduce Babel or a separate test transpiler. Keep package manifests and lockfiles synchronized.
- Templates, including Markdown notifications, belong in `templates/`; `common/messages.py` renders `templates/messages/` through Django. Keep `authn/views/openid.py`, RSS/JSON feeds, and ordinary moderator POST actions intact during frontend work.
- Keep EasyMDE and Mapbox. Preserve reply drafts, mentions, uploads, hidden coordinates, and cleanup. Reply portal wrappers participate in layout; battle replies use `.reply-form-container` in the `reply-form` grid area.
- Treat touch, keyboard, and pointer interaction equally. Use real buttons/inputs, visible errors, accessible labels, and IME-safe shortcuts. Keep native textareas on iOS/Android, including touch-enabled iPadOS. Focus reply inputs within the opening interaction; delayed focus can fail to open phone keyboards. Honor reduced motion and preserve the three-position light/system/dark control.

## CSS is our design system

- Read `theme.css`, `base.css`, `layout.css`, and the relevant `css/components/*.css` before adding styles. Reuse existing classes such as `content`, `block`, `block-header`, `button`, `form-row`, and `text-body`, plus existing template/React widgets.
- Preserve the deliberately padded/indented selector hierarchy: child and modifier rules are indented beneath the parent while remaining separate, flat CSS rules. Do not flatten formatting or convert it to Sass, CSS nesting, utility classes, or a new naming scheme.
- `theme.css` owns shared colors, fonts, and theme tokens; `base.css` owns reusable primitives; `layout.css` owns layouts/grids. Feature styles go in `css/components/<feature>.css`, imported by `css/index.css`. `components.css` is legacy: do not add new rules there.
- Use existing CSS variables and spacing/responsive patterns, including the common 570px mobile breakpoint. Account for light, dark, and automatic themes. Changes to theme detection must keep `templates/layout.html` and `ThemeSwitcher.jsx` consistent.
- Prefer shared styles over duplicate rules or new inline styles. Keep existing component-local styles local when appropriate; do not move shared design primitives into component styles. Do not add a UI kit, CSS framework, or parallel design system.

## Telegram bots

- Club bot and helpdeskbot are separate applications with independent tokens and handlers, sharing Django code and data. Keep Django setup before model/handler imports in both entry points. Both poll in debug mode and use webhooks in production.
- Telegram handlers use `async def` and await Telegram API calls. Preserve membership/moderator checks and `ensure_fresh_db_connection` around database-using entry handlers. Existing synchronous ORM code relies on the entry-point async setting; do not spread that setting globally. Work offloaded to threads must clean up its own database connections.

## Shared queue service

- The queue runs separately from Django's web process and both bots. All apps and both bots use `django_q.tasks.async_task` to enqueue async or long-running work for its workers. Queued jobs are ordinary synchronous functions; preserve their argument contracts and retry/idempotency behavior.
- Notifications are one queue workload. Reuse `notifications/telegram/common.py`, `SyncBot` in `notifications/telegram/bot.py`, and `notifications/email/sender.py`; do not add event loops or route queued sends through a running bot. Preserve recipient filtering, mute rules, and deduplication. Club notification templates live in `templates/notifications/`.

## Management commands and periodic tasks

- **Use Django management commands for both manual operations and periodic work**: maintenance, imports, backfills, rebuilds, and scheduled jobs. Put commands in the owning app's `management/commands/<name>.py`, implement `BaseCommand.handle()`, and declare options in `add_arguments()`. Run them locally with `uv run python manage.py <name> [options]`; do not add standalone Django scripts for these operations.
- Schedule periodic commands in the project's `/etc/crontab` (`etc/crontab` relative to the repository root, read as `/app/etc/crontab` by the cron service). Cron invokes the same management commands developers run manually; do not create another scheduler.

## Tests and verification

- Cover only important backend/Python business logic: access control, state transitions, payments/membership, votes, limits, privacy, and consequential bot/job decisions. Assert outcomes and persisted state. Do not add tests for templates, buttons, CSS, page wording, or notification/message text. Existing frontend/UI tests are not a precedent; leave unrelated tests and CI alone.
- Run relevant backend tests after substantial changes to business logic, persistence, permissions, or shared Python behavior, or when requested. Skip routine test runs for small edits and frontend-only changes. Use the full suite for broad backend changes.
- Browser checks, screenshots, and browser automation run **only when explicitly requested**. Use scoped lint/build checks when warranted. Review the final diff, templates, props, CSS, and affected callers; report checks actually run and any limitations.

## Deployment and configuration

Keep the existing GitHub Actions → Docker image → Docker Compose over SSH deployment in `.github/workflows/deploy.yml`, `Dockerfile`, and Compose files; no new deployment framework.

Every important new environment variable must be wired through its consumer, `club/.env.example`, and deployment configuration in the same change. For secret-backed values, add the workflow's `secret_NAME: ${{ secrets.NAME }}` mapping; update Compose environments where needed, including the queue's separate environment list. Keep test/local defaults usable, never commit real credentials, and state which GitHub secrets/variables an operator must provision.
