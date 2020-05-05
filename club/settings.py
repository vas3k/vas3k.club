import os
import random
from datetime import timedelta, datetime

import sentry_sdk
from dotenv import load_dotenv
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = os.getenv("SECRET_KEY") or "wow so secret"
DEBUG = (os.getenv("DEBUG") == "true")  # SECURITY WARNING: don"t run with debug turned on in production!

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "0.0.0.0", "vas3k.ru", "vas3k.club"]
INTERNAL_IPS = ["127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    "club",
    "auth.apps.AuthConfig",
    "comments.apps.CommentsConfig",
    "landing.apps.LandingConfig",
    "payments.apps.PaymentsConfig",
    "posts.apps.PostsConfig",
    "users.apps.UsersConfig",
    "notifications.apps.NotificationsConfig",
    "bot.apps.BotConfig",
    "search.apps.SearchConfig",
    "simple_history",
    "django_q",
    "webpack_loader",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "club.middleware.me",
    "club.middleware.ExceptionMiddleware",
]

ROOT_URLCONF = "club.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "frontend/html")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "club.context_processors.settings_processor",
                "club.context_processors.data_processor",
                "auth.context_processors.users.me",
                "posts.context_processors.topics.topics",
            ]
        },
    }
]

WSGI_APPLICATION = "club.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.getenv("POSTGRES_DB") or "vas3k_club",
        "USER": os.getenv("POSTGRES_USER") or "postgres",
        "PASSWORD": os.getenv("POSTGRES_PASSWORD") or "",
        "HOST": os.getenv("POSTGRES_HOST") or "localhost",
        "PORT": os.getenv("POSTGRES_PORT") or 5432,
    }
}

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = "ru"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "frontend/static")]

# Task queue (django-q)

REDIS_HOST = os.getenv("REDIS_HOST") or "localhost"
REDIS_PORT = os.getenv("REDIS_PORT") or 6379
Q_CLUSTER = {
    "name": "vas3k_club",
    "workers": 4,
    "recycle": 500,
    "timeout": 30,
    "compress": True,
    "save_limit": 250,
    "queue_limit": 5000,
    "redis": {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "db": os.getenv("REDIS_DB") or 0
    }
}

# Redis cache

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# App

APP_HOST = os.environ.get("APP_HOST") or "http://127.0.0.1:8000"
APP_NAME = "Вастрик.Клуб"
APP_DESCRIPTION = "Всё интересное происходит за закрытыми дверями"
LAUNCH_DATE = datetime(2020, 4, 13)

DEFAULT_PAGE_SIZE = 100
SEARCH_PAGE_SIZE = 25

SENTRY_DSN = os.getenv("SENTRY_DSN")

PATREON_AUTH_URL = "https://www.patreon.com/oauth2/authorize"
PATREON_TOKEN_URL = "https://www.patreon.com/api/oauth2/token"
PATREON_USER_URL = "https://www.patreon.com/api/oauth2/v2/identity"
PATREON_CLIENT_ID = os.getenv("PATREON_CLIENT_ID")
PATREON_CLIENT_SECRET = os.getenv("PATREON_CLIENT_SECRET")
PATREON_REDIRECT_URL = f"{APP_HOST}/auth/patreon_callback/"
PATREON_SCOPE = "identity identity[email]"
PATREON_GOD_IDS = ["8724543"]

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXP_TIMEDELTA = timedelta(days=120)

MAILGUN_API_URI = "https://api.eu.mailgun.net/v3/mailgun.vas3k.club"
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_EMAIL_FROM = "Вастрик.Клуб <club@vas3k.club>"

MEDIA_UPLOAD_URL = "https://i.vas3k.club/upload/"
MEDIA_UPLOAD_CODE = os.getenv("MEDIA_UPLOAD_CODE")
VIDEO_EXTENSIONS = {"mp4", "mov", "webm"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_BOT_URL = os.getenv("TELEGRAM_BOT_URL")
TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
TELEGRAM_ONLINE_CHANNEL_URL = os.getenv("TELEGRAM_ONLINE_CHANNEL_URL")
TELEGRAM_ONLINE_CHANNEL_ID = os.getenv("TELEGRAM_ONLINE_CHANNEL_ID")
TELEGRAM_CLUB_CHAT_URL = os.getenv("TELEGRAM_CLUB_CHAT_URL")
TELEGRAM_CLUB_CHAT_ID = os.getenv("TELEGRAM_CLUB_CHAT_ID")

SIMPLEPARSER_API_KEY = os.getenv("SIMPLEPARSER_API_KEY")

COMMENT_EDIT_TIMEDELTA = timedelta(hours=3)
RATE_LIMIT_POSTS_PER_DAY = 10
RATE_LIMIT_COMMENTS_PER_DAY = 200

POST_VIEW_COOLDOWN_PERIOD = timedelta(days=1)

WEBPACK_LOADER = {
    "DEFAULT": {
        "CACHE": not DEBUG,
        "BUNDLE_DIR_NAME": "/dist/",  # must end with slash
        "STATS_FILE": os.path.join(BASE_DIR, "frontend/webpack-stats.json"),
        "POLL_INTERVAL": 0.1,
        "TIMEOUT": None,
        "IGNORE": [r'.+\.hot-update.js', r'.+\.map'],
        "LOADER_CLASS": "webpack_loader.loader.WebpackLoader",
    }
}

if SENTRY_DSN and not DEBUG:
    # activate sentry on production
    sentry_sdk.init(dsn=SENTRY_DSN, integrations=[
        DjangoIntegration(),
        RedisIntegration(),
    ])
    Q_CLUSTER["error_reporter"] = {
        "sentry": {
            "dsn": SENTRY_DSN
        }
    }

if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
