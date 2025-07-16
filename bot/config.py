import re

from django.conf import settings

WELCOME_MESSAGE = """✖️ <b>Я — твой личный бот для PMI Russia Клуба</b>\n
Через меня можно отвечать на комменты и посты — просто напиши ответ реплаем на сообщение и я перепостю его в Клуб.
Так можно общаться в комментах даже не открывая сайт.\n
Еще в меня встроен глупый AI, который умеет искать и подсказывать всякое по Клубу.\n
Ну и я знаю всякие команды:
/top - Топ событий в Клубе
/random - Почитать случайный пост (неплохо убивает время)
/whois - Узнать профиль по телеграму
/horo - Клубный гороскоп
/auth - Привязать бота к аккаунту в Клубе
/help - Справка"""

ANONYMOUS_MESSAGE = """Привет! Мы пока не знакомы. Привяжи меня к аккаунту командой /auth с
<a href=\"https://pmi.moscow/user/me/edit/bot/\">кодом из профиля</a> через пробел"""

BOT_MENTION_RE = re.compile(rf"@{settings.TELEGRAM_BOT_URL.rsplit("/", 1).pop()}\b", re.IGNORECASE)

MIN_COMMENT_LEN = 40
SKIP_COMMANDS = ("/skip", "/Skip", "#skip", "#ignore")
COMMENT_EMOJI_RE = re.compile(r"^💬.*")
POST_EMOJI_RE = re.compile(r"^[📝🔗❓💡🏢🤜🤛🗺🗄🔥🏗🙋‍♀️].*")
COMMENT_URL_RE = re.compile(r"https?://pmi.moscow/[a-zA-Z]+/.+?/#comment-([a-fA-F0-9\-]+)")
POST_URL_RE = re.compile(r"https?://pmi.moscow/[a-zA-Z]+/(.+?)/")
