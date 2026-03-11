import os
from datetime import timedelta, datetime

import sentry_sdk
from dotenv import load_dotenv
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = os.getenv("SECRET_KEY") or "wow so secret"
DEBUG = (os.getenv("DEBUG") != "false")  # SECURITY WARNING: don't run with debug turned on in production!
TESTS_RUN = True if os.getenv("TESTS_RUN") else False

ALLOWED_HOSTS = ["*", "127.0.0.1", "localhost", "0.0.0.0", "vas3k.club", "ru.vas3k.club"]
INTERNAL_IPS = ["127.0.0.1"]

ADMINS = [
    ("admin", "club@vas3k.club"),
    ("vas3k", "me@vas3k.ru"),
]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    "club",
    "authn.apps.AuthnConfig",
    "bookmarks.apps.BookmarksConfig",
    "comments.apps.CommentsConfig",
    "landing.apps.LandingConfig",
    "payments.apps.PaymentsConfig",
    "posts.apps.PostsConfig",
    "users.apps.UsersConfig",
    "notifications.apps.NotificationsConfig",
    "search.apps.SearchConfig",
    "gdpr.apps.GdprConfig",
    "badges.apps.BadgesConfig",
    "tags.apps.TagsConfig",
    "rooms.apps.RoomsConfig",
    "misc.apps.MiscConfig",
    "godmode.apps.GodmodeConfig",
    "invites.apps.InvitesConfig",
    "tickets.apps.TicketsConfig",
    "clickers.apps.ClickersConfig",
    "ai.apps.AiConfig",
    "simple_history",
    "django_q",
    "webpack_loader",
    "helpdeskbot.apps.HelpDeskBotConfig",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.middleware.security.SecurityMiddleware",
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
            os.path.join(BASE_DIR, "helpdeskbot/templates"),
            os.path.join(BASE_DIR, "frontend/html"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "club.context_processors.settings_processor",
                "club.context_processors.features_processor",
                "users.context_processors.users.me",
                "posts.context_processors.feed.rooms",
                "posts.context_processors.feed.ordering",
            ]
        },
    }
]

WSGI_APPLICATION = "club.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

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
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB") or "vas3k_club",
        "USER": os.getenv("POSTGRES_USER") or "postgres",
        "PASSWORD": os.getenv("POSTGRES_PASSWORD") or "",
        "HOST": os.getenv("POSTGRES_HOST") or "localhost",
        "PORT": os.getenv("POSTGRES_PORT") or 5432,
    }
}

if bool(os.getenv("POSTGRES_USE_POOLING")):
    DATABASES["default"]["OPTIONS"] = {
        "pool": {
            "min_size": 5,
            "max_size": 15,
            "timeout": 10, # fail in 10 sec under load
            "max_idle": 300, # close idle after 5 min
        }
    }
else:
    DATABASES["default"]["CONN_MAX_AGE"] = 0
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True


# Internationalization

LANGUAGE_CODE = "ru"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = False

# Static files (CSS, JavaScript, Images)

STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "frontend/static")]

# Task queue (django-q)

REDIS_HOST = os.getenv("REDIS_HOST") or "localhost"
REDIS_PORT = os.getenv("REDIS_PORT") or 6379
Q_CLUSTER = {
    "name": "vas3k_club",
    "workers": 4,
    "recycle": 500,
    "timeout": 300,
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
        "TIMEOUT": 3600,  # 5 hours max
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        }
    }
}

LANDING_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

# Email

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "email-smtp.eu-central-1.amazonaws.com")
EMAIL_PORT = os.getenv("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Вастрик.Клуб <club@vas3k.club>")

# App

APP_HOST = os.environ.get("APP_HOST") or "http://127.0.0.1:8000"
LAUNCH_DATE = datetime(2020, 4, 13)

AUTH_CODE_LENGTH = 6
AUTH_CODE_EXPIRATION_TIMEDELTA = timedelta(minutes=10)
AUTH_MAX_CODE_TIMEDELTA = timedelta(hours=3)
AUTH_MAX_CODE_COUNT = 3
AUTH_MAX_CODE_ATTEMPTS = 3

DEFAULT_PAGE_SIZE = 70
SEARCH_PAGE_SIZE = 25
PEOPLE_PAGE_SIZE = 18
PROFILE_COMMENTS_PAGE_SIZE = 100
PROFILE_POSTS_PAGE_SIZE = 30
FRIENDS_PAGE_SIZE = 30
PROFILE_BADGES_PAGE_SIZE = 50

COMMUNITY_APPROVE_UPVOTES = 35

GDPR_ARCHIVE_STORAGE_PATH = os.getenv("GDPR_ARCHIVE_STORAGE_PATH") or os.path.join(BASE_DIR, "gdpr/downloads")
GDPR_ARCHIVE_URL = "/downloads/"
GDPR_ARCHIVE_REQUEST_TIMEDELTA = timedelta(hours=6)
GDPR_ARCHIVE_DELETE_TIMEDELTA = timedelta(hours=24)
GDPR_DELETE_CODE_LENGTH = 14
GDPR_DELETE_CONFIRMATION = "я готов удалиться навсегда"
GDPR_DELETE_TIMEDELTA = timedelta(hours=2 * 24)

SENTRY_DSN = os.getenv("SENTRY_DSN")

PATREON_AUTH_URL = "https://www.patreon.com/oauth2/authorize"
PATREON_TOKEN_URL = "https://www.patreon.com/api/oauth2/token"
PATREON_USER_URL = "https://www.patreon.com/api/oauth2/v2/identity"
PATREON_CLIENT_ID = os.getenv("PATREON_CLIENT_ID")
PATREON_CLIENT_SECRET = os.getenv("PATREON_CLIENT_SECRET")
PATREON_REDIRECT_URL = f"{APP_HOST}/auth/patreon_callback/"
PATREON_SCOPE = "identity identity[email]"

JWT_PRIVATE_KEY = (os.getenv("JWT_PRIVATE_KEY") or "").replace("\\n", "\n")
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

OPENID_JWT_ALGORITHM = "RS256"
OPENID_JWT_EXPIRE_SECONDS = 24 * 60 * 60  # 24 hours
OPENID_CODE_EXPIRE_SECONDS = 300  # 5 minutes

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

MEDIA_UPLOAD_URL = "https://i.vas3k.club/upload/multipart/"
MEDIA_UPLOAD_CODE = os.getenv("MEDIA_UPLOAD_CODE")
VIDEO_EXTENSIONS = {"mp4", "mov", "webm"}
IMAGE_EXTENSIONS = {"webp", "jpg", "jpeg", "png", "gif"}

OG_IMAGE_GENERATOR_URL = "https://og.vas3k.club/preview"
OG_IMAGE_DEFAULT = "https://vas3k.club/static/images/share.png"
OG_MACHINE_AUTHOR_LOGO = "https://vas3k.club/static/images/the_machine_logo.png"
OG_IMAGE_GENERATOR_DEFAULTS = {
    "logo": "https://vas3k.club/static/images/logo/logo-white-text.png",
    "op": 0.6,
    "bg": "#FFFFFF",
}

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_BOT_URL = os.getenv("TELEGRAM_BOT_URL") or "https://t.me/vas3k_club_bot"
TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
TELEGRAM_VIBES_CHAT_ID = -1002158547445
TELEGRAM_PARLIAMENT_CHAT_ID = -1001148097898
TELEGRAM_CLUB_CHANNEL_URL = os.getenv("TELEGRAM_CLUB_CHANNEL_URL")
TELEGRAM_CLUB_CHANNEL_ID = os.getenv("TELEGRAM_CLUB_CHANNEL_ID")
TELEGRAM_CLUB_CHAT_ID = os.getenv("TELEGRAM_CLUB_CHAT_ID")
TELEGRAM_ONLINE_CHANNEL_URL = os.getenv("TELEGRAM_ONLINE_CHANNEL_URL")
TELEGRAM_ONLINE_CHANNEL_ID = os.getenv("TELEGRAM_ONLINE_CHANNEL_ID")
TELEGRAM_PAY_BOT_URL = "https://t.me/vas3kpaybot"
TELEGRAM_BOT_WEBHOOK_URL = "https://vas3k.club/telegram/webhook/"
TELEGRAM_BOT_WEBHOOK_HOST = "0.0.0.0"
TELEGRAM_BOT_WEBHOOK_PORT = 8816
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY") or ""
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY") or ""
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET") or ""
STRIPE_CANCEL_URL = APP_HOST + "/join/"
STRIPE_SUCCESS_URL = APP_HOST + "/monies/done/?reference={CHECKOUT_SESSION_ID}"
STRIPE_CUSTOMER_PORTAL_URL = "https://billing.stripe.com/p/login/6oEcMM7Sj7YfaWIbII"

WEBHOOK_SECRETS = set(os.getenv("WEBHOOK_SECRETS", "").split(","))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DEFAULT_AVATAR = "https://i.vas3k.club/v.png"
COMMENT_EDITABLE_TIMEDELTA = timedelta(hours=48)
COMMENT_DELETABLE_TIMEDELTA = timedelta(days=10 * 365)
COMMENT_DELETABLE_BY_POST_AUTHOR_TIMEDELTA = timedelta(days=14)
RETRACT_VOTE_IN_HOURS = 24
RETRACT_VOTE_TIMEDELTA = timedelta(hours=RETRACT_VOTE_IN_HOURS)
RATE_LIMIT_POSTS_PER_DAY = 3
RATE_LIMIT_COMMENTS_PER_DAY = 100
RATE_LIMIT_COMMENT_PER_DAY_CUSTOM_KEY = "comments_per_day"
POST_VIEW_COOLDOWN_PERIOD = timedelta(days=1)  # how much time must pass before a repeat viewing of a post counts
POST_HOTNESS_PERIOD = timedelta(days=5)  # time window for hotness recalculation script
MAX_COMMENTS_FOR_DELETE_VS_CLEAR = 10  # number of comments after which the post cannot be deleted
MIN_DAYS_TO_GIVE_BADGES = 50  # minimum "days" balance to buy and gift any badge
MAX_MUTE_COUNT = 25  # maximum number of users allowed to mute
CLEARED_POST_TEXT = "```\n" \
    "😥 Этот пост был удален самим автором и от него остались лишь комментарии участников. " \
    "Если вы хотите приютить и развить эту тему как новый автор, напишите модераторам Клуба: moderator@vas3k.club." \
    "\n```"


MODERATOR_USERNAME = "moderator"
DELETED_USERNAME = "deleted"

VALUES_GUIDE_URL = "https://vas3k.club/post/values/"
POSTING_GUIDE_URL = "https://vas3k.club/post/10447/"
CHATS_GUIDE_URL = "https://vas3k.club/post/9542/"
PEOPLE_GUIDE_URL = "https://vas3k.club/post/2584/"

CREWS = {
    "vibes": {
        "title": "Написать в Министерство Вайбов",
        "telegram_chat_id": TELEGRAM_VIBES_CHAT_ID,
        "reasons": [
            {"code": "vibe", "text": "Делюсь вайбом!"},
            {"code": "novibe", "text": "Кто-то не вайбит!"},
            {"code": "interesting", "text": "Принёс вам интересненькое"},
            {"code": "other", "text": "Другое"},
        ]
    },
    "parliament": {
        "title": "Написать в Парламент",
        "telegram_chat_id": TELEGRAM_PARLIAMENT_CHAT_ID,
        "reasons": [
            {"code": "achievement", "text": "Выдать или получить ачивку"},
            {"code": "activity", "text": "Хочу организовать активность"},
            {"code": "idea", "text": "У меня есть идея для Клуба!"},
            {"code": "other", "text": "Я только спросить"},
        ]
    },
    "events": {
        "title": "Написать оргам Вастрик Ивентов",
        "telegram_chat_id": -1003410014342,
    }
}


SUPPORTED_TIME_ZONES = [
	("UTC", "по UTC"),
	("Asia/Almaty", "по Алматы"),
	("Europe/Amsterdam", "по Амстердаму"),
	("Europe/Belgrade", "по Белграду"),
	("Europe/Berlin", "по Берлину"),
	("America/Argentina/Buenos_Aires", "по Буэнос-Айресу"),
	("America/Vancouver", "по Ванкуверу"),
	("Europe/Warsaw", "по Варшаве"),
	("Europe/Vienna", "по Вене"),
	("Europe/Vilnius", "по Вильнюсу"),
	("Asia/Vladivostok", "по Владивостоку"),
    ("Europe/Athens", "по Греции"),
	("Asia/Hong_Kong", "по Гонконгу"),
	("America/Denver", "по Денверу"),
	("Asia/Dubai", "по Дубаю"),
	("Europe/Dublin", "по Дублину"),
	("Asia/Yekaterinburg", "по Екатеринбургу"),
	("Asia/Yerevan", "по Еревану"),
	("Asia/Jerusalem", "по Израилю"),
	("Asia/Irkutsk", "по Иркутску"),
	("Asia/Kamchatka", "по Камчатке"),
	("Africa/Johannesburg", "по Кейптауну"),
	("Europe/Kyiv", "по Киеву"),
	("Europe/Chisinau", "по Кишиневу"),
	("Europe/Copenhagen", "по Копенгагену"),
	("Asia/Krasnoyarsk", "по Красноярску"),
	("Asia/Kuala_Lumpur", "по Куала-Лумпуру"),
	("Europe/Lisbon", "по Лиссабону"),
	("Europe/London", "по Лондону"),
	("America/Los_Angeles", "по Лос-Анджелесу"),
	("Asia/Magadan", "по Магадану"),
	("Europe/Madrid", "по Мадриду/Барселоне"),
	("America/Mexico_City", "по Мехико"),
	("Europe/Moscow", "по Москве"),
	("Asia/Novosibirsk", "по Новосибирску"),
	("America/New_York", "по Нью-Йорку"),
	("Pacific/Auckland", "по Окленду"),
	("Asia/Omsk", "по Омску"),
	("Europe/Paris", "по Парижу"),
	("Europe/Prague", "по Праге"),
	("Europe/Riga", "по Риге"),
	("Europe/Rome", "по Риму"),
	("Europe/Samara", "по Самаре"),
	("America/Sao_Paulo", "по Сан-Паулу"),
	("Asia/Seoul", "по Сеулу"),
	("Australia/Sydney", "по Сиднею"),
	("Asia/Singapore", "по Сингапуру"),
	("Europe/Istanbul", "по Стамбулу"),
	("Europe/Stockholm", "по Стокгольму"),
	("Asia/Bangkok", "по Таиланду"),
	("Europe/Tallinn", "по Таллину"),
	("Asia/Samarkand", "по Ташкенту"),
	("Asia/Tbilisi", "по Тбилиси"),
	("Asia/Tokyo", "по Токио"),
	("America/Toronto", "по Торонто"),
	("Europe/Helsinki", "по Хельсинки"),
	("Europe/Zurich", "по Цюриху"),
	("America/Chicago", "по Чикаго"),
	("Asia/Shanghai", "по Шанхаю"),
	("Asia/Yakutsk", "по Якутску")
]

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

if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
