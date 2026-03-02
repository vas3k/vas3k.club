import asyncio
import logging
import threading

from asgiref.sync import async_to_sync
from telegram import Bot
from django.conf import settings

log = logging.getLogger(__name__)


class SyncBot:
    """Synchronous proxy for async ``telegram.Bot`` (PTB v22).

    Lazily calls ``bot.initialize()`` on first use.
    """

    def __init__(self, tg_bot: Bot):
        self._bot = tg_bot
        self._initialized = False
        self._lock = threading.Lock()

    def _ensure_initialized(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    async_to_sync(self._bot.initialize)()
                    self._initialized = True

    @property
    def bot(self) -> Bot:
        self._ensure_initialized()
        return self._bot

    def __getattr__(self, name):
        self._ensure_initialized()
        attr = getattr(self._bot, name)
        if asyncio.iscoroutinefunction(attr):
            wrapped = async_to_sync(attr)
            setattr(self, name, wrapped)
            return wrapped
        return attr

    def __repr__(self):
        status = "initialized" if self._initialized else "not initialized"
        return f"<SyncBot({status})>"


bot = SyncBot(Bot(token=settings.TELEGRAM_TOKEN)) if settings.TELEGRAM_TOKEN else None
