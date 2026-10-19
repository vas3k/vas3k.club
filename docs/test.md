# Testing

Cover important backend/Python business logic: permissions, state changes, payments, membership, votes, limits, privacy, and consequential bot/queue decisions. Assert outcomes and persisted state, not templates, buttons, CSS, or page/notification wording. Mock external services and queued sends.

Run relevant tests after substantial backend changes or when requested. Use the full suite for broad backend changes. Browser checks run only when explicitly requested.

## Existing Docker development stack

```sh
docker compose exec -e TESTS_RUN=true club_app python3 manage.py test payments.tests
docker compose exec -e TESTS_RUN=true club_app python3 manage.py test
```

## Native uv

Complete [native setup](setup.md#native-python-with-uv), including the frontend build and reachable PostgreSQL/Redis services. The PostgreSQL role must be allowed to create test databases.

```sh
TESTS_RUN=true uv run python manage.py test payments.tests
TESTS_RUN=true uv run python manage.py test
```

`TESTS_RUN` enables the project's test settings; set it only for test commands. [CI](../.github/workflows/tests.yml) runs Flake8, the backend suite, and the existing frontend Jest suite. The separate [build check](../.github/workflows/check_build_and_run.yml) verifies Docker startup and webpack compilation.
