import asyncio
import functools
import logging
import threading

from telegram import Bot
from django.conf import settings

log = logging.getLogger(__name__)


class SyncBot:
    """Synchronous wrapper for async telegram.Bot (PTB v22)."""

    def __init__(self, tg_bot: Bot):
        self._bot = tg_bot
        self._initialized = False
        self._lock = threading.Lock()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def _ensure_initialized(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    future = asyncio.run_coroutine_threadsafe(self._bot.initialize(), self._loop)
                    future.result()
                    self._initialized = True

    @property
    def bot(self) -> Bot:
        self._ensure_initialized()
        return self._bot

    def _wrap_async(self, method):
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            future = asyncio.run_coroutine_threadsafe(method(*args, **kwargs), self._loop)
            return future.result()
        return wrapper

    def __getattr__(self, name):
        self._ensure_initialized()
        attr = getattr(self._bot, name)
        if asyncio.iscoroutinefunction(attr):
            wrapper = self._wrap_async(attr)
            setattr(self, name, wrapper)
            return wrapper
        return attr

    def __repr__(self):
        status = "initialized" if self._initialized else "not initialized"
        return f"<SyncBot({status})>"


bot = SyncBot(Bot(token=settings.TELEGRAM_TOKEN)) if settings.TELEGRAM_TOKEN else None
