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
DEBUG = (os.getenv("DEBUG") == "true")  # SECURITY WARNING: don't run with debug turned on in production!
TESTS_RUN = True if os.getenv("TESTS_RUN") else False

ALLOWED_HOSTS = ["*", "127.0.0.1", "localhost", "0.0.0.0", "vas3k.club"]
INTERNAL_IPS = ["127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    "club",
    "auth.apps.AuthConfig",
    "bookmarks.apps.BookmarksConfig",
    "comments.apps.CommentsConfig",
    "landing.apps.LandingConfig",
    "payments.apps.PaymentsConfig",
    "posts.apps.PostsConfig",
    "users.apps.UsersConfig",
    "notifications.apps.NotificationsConfig",
    "search.apps.SearchConfig",
    "gdpr.apps.GdprConfig",
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
        "DIRS": [
            os.path.join(BASE_DIR, "notifications/telegram/templates"),
            os.path.join(BASE_DIR, "frontend/html"),
        ],
        "APP_DIRS": False,
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

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler"
        },
    },
    "loggers": {
        "": {  # "catch all" loggers by referencing it with the empty string
            "handlers": ["console"],
            "level": "DEBUG",
        },
    },
}

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

LANDING_CACHE_TIMEOUT = 60 * 60 * 24

# App

APP_HOST = os.environ.get("APP_HOST") or "http://127.0.0.1:8000"
APP_NAME = "Вастрик.Клуб"
APP_DESCRIPTION = "Всё интересное происходит за закрытыми дверями"
LAUNCH_DATE = datetime(2020, 4, 13)

AUTH_CODE_LENGTH = 6
AUTH_CODE_EXPIRATION_TIMEDELTA = timedelta(minutes=15)
AUTH_MAX_CODE_TIMEDELTA = timedelta(hours=1)
AUTH_MAX_CODE_COUNT = 5
AUTH_MAX_CODE_ATTEMPTS = 3

DEFAULT_PAGE_SIZE = 70
SEARCH_PAGE_SIZE = 25
PEOPLE_PAGE_SIZE = 18

COMMUNITY_APPROVE_UPVOTES = 20

GDPR_ARCHIVE_STORAGE_PATH = os.getenv("GDPR_ARCHIVE_STORAGE_PATH") or os.path.join(BASE_DIR, "gdpr/downloads")
GDPR_ARCHIVE_URL = "/downloads/"
GDPR_ARCHIVE_REQUEST_TIMEDELTA = timedelta(hours=6)
GDPR_ARCHIVE_DELETE_TIMEDELTA = timedelta(hours=24)
GDPR_DELETE_CODE_LENGTH = 14
GDPR_DELETE_CONFIRMATION = "я готов удалиться навсегда"
GDPR_DELETE_TIMEDELTA = timedelta(hours=5 * 24)

SENTRY_DSN = os.getenv("SENTRY_DSN")

PATREON_AUTH_URL = "https://www.patreon.com/oauth2/authorize"
PATREON_TOKEN_URL = "https://www.patreon.com/api/oauth2/token"
PATREON_USER_URL = "https://www.patreon.com/api/oauth2/v2/identity"
PATREON_CLIENT_ID = os.getenv("PATREON_CLIENT_ID")
PATREON_CLIENT_SECRET = os.getenv("PATREON_CLIENT_SECRET")
PATREON_REDIRECT_URL = f"{APP_HOST}/auth/patreon_callback/"
PATREON_SCOPE = "identity identity[email]"
PATREON_GOD_IDS = ["8724543"]

JWT_PRIVATE_KEY = os.getenv("JWT_PRIVATE_KEY")
JWT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAvEDEGKL0b+okI6QBBMiu
3GOHOG/Ml4KJ13tWyPnl5yGswf9rUGOLo0T0dXxSwxp/6g1ZeYqDR7jckuP6A3Rv
DPdKYc44eG3YB/bO2Yeq57Kx1rxvFvWZap2jTyu2wbALmmeg0ne3wkXPExTy/EQ4
LDft8nraSJuW7c+qrah+F94qKGVNvilf20V5S186iGpft2j/UAl9s81kzZKBwk7M
B+u4jSH8E3KHZVb28CVNOpnYYcLBNLsjGwZk6qbiuq1PEq4AZ5TN3EdoVP9nbIGY
BZAMwoNxP4YQN+mDRa6BU2Mhy+c9ea+fuCKRxNi3+nYjF00D28fErFFcA+BEe4A1
Hhq25PsVfUgOYvpv1F/ImPJBl8q728DEzDcj1QzL0flbPUMBV6Bsq+l2X3OdrVtQ
GXiwJfJRWIVRVDuJzdH+Te2bvuxk2d0Sq/H3uzXYd/IQU5Jw0ZZRTKs+Rzdpb8ui
eoDmq2uz6Q2WH2gPwyuVlRfatJOHCUDjd6dE93lA0ibyJmzxo/G35ns8sZoZaJrW
rVdFROm3nmAIATC/ui9Ex+tfuOkScYJ5OV1H1qXBckzRVwfOHF0IiJQP4EblLlvv
6CEL2VBz0D2+gE4K4sez6YSn3yTg9TkWGhXWCJ7vomfwIfHIdZsItqay156jMPaV
c+Ha7cw3U+n6KI4idHLiwa0CAwEAAQ==
-----END PUBLIC KEY-----"""
JWT_ALGORITHM = "RS256"
JWT_EXP_TIMEDELTA = timedelta(days=120)

MAILGUN_API_URI = "https://api.eu.mailgun.net/v3/mailgun.vas3k.club"
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_EMAIL_FROM = "Вастрик.Клуб <club@vas3k.club>"

MEDIA_UPLOAD_URL = "https://i.vas3k.club/upload/multipart/"
MEDIA_UPLOAD_CODE = os.getenv("MEDIA_UPLOAD_CODE")
VIDEO_EXTENSIONS = {"mp4", "mov", "webm"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_BOT_URL = os.getenv("TELEGRAM_BOT_URL")
TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
TELEGRAM_CLUB_CHANNEL_URL = os.getenv("TELEGRAM_CLUB_CHANNEL_URL")
TELEGRAM_CLUB_CHANNEL_ID = os.getenv("TELEGRAM_CLUB_CHANNEL_ID")
TELEGRAM_CLUB_CHAT_URL = os.getenv("TELEGRAM_CLUB_CHAT_URL")
TELEGRAM_CLUB_CHAT_ID = os.getenv("TELEGRAM_CLUB_CHAT_ID")
TELEGRAM_ONLINE_CHANNEL_URL = os.getenv("TELEGRAM_ONLINE_CHANNEL_URL")
TELEGRAM_ONLINE_CHANNEL_ID = os.getenv("TELEGRAM_ONLINE_CHANNEL_ID")
TELEGRAM_BOT_WEBHOOK_URL = "https://vas3k.club/telegram/webhook/"
TELEGRAM_BOT_WEBHOOK_HOST = "0.0.0.0"
TELEGRAM_BOT_WEBHOOK_PORT = 8816

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY") or ""
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY") or ""
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET") or ""
STRIPE_CANCEL_URL = APP_HOST + "/join/"
STRIPE_SUCCESS_URL = APP_HOST + "/monies/done/?reference={CHECKOUT_SESSION_ID}"

COMMENT_EDITABLE_TIMEDELTA = timedelta(hours=24)
COMMENT_DELETABLE_TIMEDELTA = timedelta(days=10 * 365)
COMMENT_DELETABLE_BY_POST_AUTHOR_TIMEDELTA = timedelta(days=14)
RETRACT_VOTE_IN_HOURS = 3
RETRACT_VOTE_TIMEDELTA = timedelta(hours=RETRACT_VOTE_IN_HOURS)
RATE_LIMIT_POSTS_PER_DAY = 10
RATE_LIMIT_COMMENTS_PER_DAY = 200

POST_VIEW_COOLDOWN_PERIOD = timedelta(days=1)
POST_HOTNESS_PERIOD = timedelta(days=5)

MAX_COMMENTS_FOR_DELETE_VS_CLEAR = 10
CLEARED_POST_TEXT = "```\n" \
    "😥 Этот пост был удален самим автором и от него остались лишь комментарии участников. " \
    "Если вы хотите приютить и развить эту тему как новый автор, напишите модераторам Клуба: moderator@vas3k.club." \
    "\n```"

MODERATOR_USERNAME = "moderator"
DELETED_USERNAME = "deleted"

WEBPACK_LOADER = {
    "DEFAULT": {
        "CACHE": not DEBUG,
        "BUNDLE_DIR_NAME": "/dist/",  # must end with slash
        "STATS_FILE": os.path.join(BASE_DIR, "frontend/webpack-stats.json"),
        "POLL_INTERVAL": 0.1,
        "TIMEOUT": None,
        "IGNORE": [r".+\.hot-update.js", r".+\.map"],
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

# if DEBUG:
#     INSTALLED_APPS += ["debug_toolbar"]
#     MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
