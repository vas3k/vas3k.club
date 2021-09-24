import types

import sentry_sdk
from club.settings import *  # noqa: F401,F403

DATABASES = types.MappingProxyType({
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME":"4aff",
        "USER": "root",
        "PASSWORD": "root",
        "HOST": "localhost",
        "PORT": 5432,
    }
})

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://localhost:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

sentry_sdk.init(dsn="", integrations=[], send_default_pii=False)

DEBUG = True
TESTS_RUN = True
