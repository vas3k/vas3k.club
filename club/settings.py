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

ALLOWED_HOSTS = ["*", "127.0.0.1", "localhost", "0.0.0.0", "pmi.moscow"]
INTERNAL_IPS = ["127.0.0.1"]

ADMINS = [
    ("TopTuK", "sergey.sidorov@pmi.moscow"),
]

INSTALLED_APPS = [
    "django.contrib.auth",  # FIXME: do we need this?
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
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
    "ai.apps.AiConfig",
    "simple_history",
    "django_q",
    "webpack_loader",
    "helpdeskbot.apps.HelpDeskBotConfig",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
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
                "django.contrib.messages.context_processors.messages",
                "django.contrib.auth.context_processors.auth",
                "club.context_processors.settings_processor",
                "club.context_processors.features_processor",
                "authn.context_processors.users.me",
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
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.getenv("POSTGRES_DB") or "pmi_club",
        "USER": os.getenv("POSTGRES_USER") or "pmiclub",
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
    "name": "pmi_club",
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

LANDING_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

# Email

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "mail.pmi.moscow")
EMAIL_PORT = os.getenv("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "PM Russia Club <club@pmi.moscow>")

# App
APP_HOST = os.environ.get("APP_HOST") or "http://127.0.0.1:8000"
APP_NAME = "PM Club Russia"
APP_DESCRIPTION = "Всё интересное происходит за закрытыми дверями"
LAUNCH_DATE = datetime(2022, 8, 1)

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

PATREON_CLIENT_ID = os.getenv("PATREON_CLIENT_ID") or ""
PATREON_CLIENT_SECRET = os.getenv("PATREON_CLIENT_SECRET") or ""

PATREON_REDIRECT_URL = f"{APP_HOST}/auth/patreon_callback/"
PATREON_SCOPE = "identity identity[email]"

COINBASE_CHECKOUT_ENDPOINT = "https://commerce.coinbase.com/checkout/"
COINBASE_WEBHOOK_SECRET = os.getenv("COINBASE_WEBHOOK_SECRET")

JWT_PRIVATE_KEY = (os.getenv("JWT_PRIVATE_KEY") or "").replace("\\n", "\n")
JWT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA03rHsNGQ3HUfHIqSYXCh
dCAl8S4hlhCwNK7OPqh7oWVW8O/UFMqdQ1OMxb95iTIDx/as65crXVFx6X/PWBkx
w2qRLcK+r7XXPsfIGmvlJC/TDsoHx86QXutsmLFSjAmr5MyvV7S1178cf5OqdXZH
HB0nZpM+UlncbcHbQuEgcVmsn2JurJzvAFE8DUu887Kcv+e8fLXc5DVVE3IKKW20
DoZOn2kTPSw7oS75qmDIXw5aa6B5S93MFFy09kwwnfemZkQ9Sa2Ae14SugxmBns6
1BS9+KNxFUdlWLADSh8N2Yho8PnIu1O5KL/pnQxByVsXYF2aU6+zTkeLM814VFYI
knYX4sHDZHl8lco7gDxC5Fo9m46CFgBjirJE6y/5BJ+PggmpwXwN8JQvRZ9aCIS1
qktKiGnql5817Gr4VdTouQBS4ITZq/Ly+lAIKc3E5R+7VNgjW9kiDb+nPmNcb+Dg
FrszQVIzss9rVZWGHBX0IihkBHkUpPgtzulzk3LzWpr7bsRqW+lHeLdUCqNE35k5
3rHVnhAXzoHYT6csfDfAB441Zrf8X7BjTINGqiRY2yPjYdXkGrdRaU0p3Cfm/x5+
pDj7UCL9iaN+xZdV4IULs3OvwLY+iuVKQR/Ja5lnyazAMZHBjIDBejHd/3hXlUBL
BbPun08UBA4T4QntAsUVfvsCAwEAAQ==
-----END PUBLIC KEY-----"""

OPENID_JWT_ALGORITHM = "RS256"
OPENID_JWT_EXPIRE_SECONDS = 24 * 60 * 60  # 24 hours
OPENID_CODE_EXPIRE_SECONDS = 300  # 5 minutes

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

MEDIA_UPLOAD_URL = "https://media.pmi.moscow/upload/multipart/"
MEDIA_UPLOAD_CODE = os.getenv("MEDIA_UPLOAD_CODE")
VIDEO_EXTENSIONS = {"mp4", "mov", "webm"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}

OG_IMAGE_GENERATOR_URL = "https://og.pmi.moscow/preview"
OG_IMAGE_DEFAULT = "https://pmi.moscow/static/images/pmi_share.png"
OG_MACHINE_AUTHOR_LOGO = "https://pmi.moscow/static/images/the_machine_logo.png"
OG_IMAGE_GENERATOR_DEFAULTS = {
    "logo": "https://pmi.moscow/static/images/logo/logo-white-text.png",
    "op": 0.6,
    "bg": "#FFFFFF",
}

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_BOT_URL = os.getenv("TELEGRAM_BOT_URL") or "https://t.me/pmiclubbot"
TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
TELEGRAM_CLUB_CHANNEL_URL = os.getenv("TELEGRAM_CLUB_CHANNEL_URL")
TELEGRAM_CLUB_CHANNEL_ID = os.getenv("TELEGRAM_CLUB_CHANNEL_ID")
TELEGRAM_CLUB_CHAT_URL = os.getenv("TELEGRAM_CLUB_CHAT_URL")
TELEGRAM_CLUB_CHAT_ID = os.getenv("TELEGRAM_CLUB_CHAT_ID")
TELEGRAM_ONLINE_CHANNEL_URL = os.getenv("TELEGRAM_ONLINE_CHANNEL_URL")
TELEGRAM_ONLINE_CHANNEL_ID = os.getenv("TELEGRAM_ONLINE_CHANNEL_ID")
TELEGRAM_PAY_BOT_URL = "https://t.me/vas3kpaybot"
TELEGRAM_BOT_WEBHOOK_URL = "https://pmi.moscow/telegram/webhook/"
TELEGRAM_BOT_WEBHOOK_HOST = "0.0.0.0"
TELEGRAM_BOT_WEBHOOK_PORT = 8816

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY") or ""
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY") or ""
STRIPE_CANCEL_URL = APP_HOST + "/join/"
STRIPE_SUCCESS_URL = APP_HOST + "/monies/done/?reference={CHECKOUT_SESSION_ID}"
STRIPE_CUSTOMER_PORTAL_URL = "https://billing.stripe.com/p/login/6oEcMM7Sj7YfaWIbII"

WEBHOOK_SECRETS = set(os.getenv("WEBHOOK_SECRETS", "").split(","))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_CHAT_MODEL = "gpt-4.1-mini"
OPENAI_EMBEDDINGS_MODEL = "text-embedding-3-small"
OPENAI_EMBEDDINGS_VECTOR_DIM = 1536

DEFAULT_AVATAR = "https://media.pmi.moscow/30095075d17a92786cfea143a73d68f5f1b3e71173e3f4ecf16f90d25834e45e.png"
COMMENT_EDITABLE_TIMEDELTA = timedelta(hours=24)
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
    "Если вы хотите приютить и развить эту тему как новый автор, напишите модераторам Клуба: moderator@pmi.moscow" \
    "\n```"


MODERATOR_USERNAME = "moderator"
DELETED_USERNAME = "deleted"


VALUES_GUIDE_URL = "https://pmi.moscow/post/103/"
POSTING_GUIDE_URL = "https://pmi.moscow/post/9/"
CHATS_GUIDE_URL = "https://pmi.moscow/post/12/"
PEOPLE_GUIDE_URL = "https://pmi.moscow/post/13/"
PARLIAMENT_GUIDE_URL = "https://pmi.moscow/post/15/"

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
