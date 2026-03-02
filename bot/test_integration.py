import asyncio
import json
import logging
import socket
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import patch

import django
from django.conf import settings
from django.test import TestCase, override_settings

from bot.main import build_application
import bot.config

django.setup()

import requests
import urllib3
from telegram import Update, Message, User as TgUser, Chat as TgChat, MessageEntity
from telegram.ext import Application

from notifications.telegram.tests import BaseTelegramTest, ExpectedRequest, Request
from users.models.user import User

log = logging.getLogger(__name__)


class BotIntegrationTest(BaseTelegramTest, TestCase):
    tags = {"telegram", "telegram_bot", "telegram_integration"}

    TELEGRAM_TOKEN_VALUE = BaseTelegramTest.TOKEN

    SEND_MESSAGE_RESPONSE = json.dumps(
        {
            "ok": True,
            "result": {
                "message_id": 123456,
                "date": int(time.time()),
                "chat": {"id": 12345, "type": "private"},
                "text": "test",
                "from": {
                    "id": 987654321,
                    "is_bot": True,
                    "first_name": "TestBot",
                },
            },
        }
    )

    SEND_CHAT_ACTION_RESPONSE = json.dumps({"ok": True, "result": True})

    GET_ME_RESPONSE = json.dumps(
        {
            "ok": True,
            "result": {
                "id": 987654321,
                "is_bot": True,
                "first_name": "TestBot",
                "username": "test_bot",
            },
        }
    )

    SET_WEBHOOK_RESPONSE = json.dumps({"ok": True, "result": True})

    _application: Application | None
    _event_loop: asyncio.AbstractEventLoop | None

    def setUp(self):
        super().setUp()

        server_port = self.server.server_address[1]
        telegram_base_url = f"http://127.0.0.1:{server_port}/bot"

        now = datetime.now(timezone.utc)
        self.test_user = User.objects.create(
            slug="test-user",
            email="test@example.com",
            full_name="Test User",
            secret_hash="test_secret_hash",
            telegram_id="999",
            membership_started_at=now,
            membership_expires_at=now + timedelta(days=30),
            moderation_status=User.MODERATION_STATUS_APPROVED,
        )

        # Prevent ensure_fresh_db_connection from closing the test DB connection
        self.close_old_connections_patch = patch(
            "bot.decorators.close_old_connections"
        )
        self.close_old_connections_patch.start()

        self.settings_override = override_settings(
            TELEGRAM_BASE_URL=telegram_base_url,
            TELEGRAM_TOKEN=BaseTelegramTest.TOKEN,
            TELEGRAM_ADMIN_CHAT_ID="123456789",
            TELEGRAM_BOT_WEBHOOK_URL=telegram_base_url,
            DEBUG=False,
        )
        self.settings_override.enable()

        self._application = None
        self._event_loop = None

    def tearDown(self):
        if self._application and self._event_loop:
            async def _stop():
                if self._application.updater and self._application.updater.running:
                    await self._application.updater.stop()
                if self._application.running:
                    await self._application.stop()
                    await self._application.shutdown()

            asyncio.run_coroutine_threadsafe(_stop(), self._event_loop).result(timeout=5)

        self.close_old_connections_patch.stop()
        self.settings_override.disable()

        super().tearDown()

    def _start_application_in_thread(self, application, mode="webhook"):
        """Start the application in a background thread using non-blocking API."""
        started = threading.Event()

        async def _run():
            self._event_loop = asyncio.get_running_loop()
            await application.initialize()
            await application.start()

            if mode == "webhook":
                await application.updater.start_webhook(
                    listen=settings.TELEGRAM_BOT_WEBHOOK_HOST,
                    port=settings.TELEGRAM_BOT_WEBHOOK_PORT,
                    url_path=settings.TELEGRAM_TOKEN,
                    webhook_url=settings.TELEGRAM_BOT_WEBHOOK_URL + settings.TELEGRAM_TOKEN,
                )
            else:
                await application.updater.start_polling()

            started.set()
            # Keep the loop running until stopped
            while application.running:
                await asyncio.sleep(0.1)

        def _thread_target():
            asyncio.run(_run())

        thread = threading.Thread(target=_thread_target, daemon=True)
        thread.start()
        started.wait(timeout=5)

    def _create_update(
        self, message_text: str, reply_to_text: Optional[str] = None
    ) -> Update:
        telegram_id = int(self.test_user.telegram_id or "")
        tg_user = TgUser(id=telegram_id, is_bot=False, first_name="Test")
        tg_chat = TgChat(id=12345, type="private")

        reply_to_message = None
        if reply_to_text:
            reply_to_message = Message(
                message_id=0,
                date=datetime.now(timezone.utc),
                chat=tg_chat,
                text=reply_to_text,
                from_user=TgUser(id=6789, is_bot=False, first_name="First"),
            )

        message = Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=tg_chat,
            from_user=tg_user,
            text=message_text,
            reply_to_message=reply_to_message,
        )

        update = Update(update_id=1, message=message)
        return update

    def _create_command_update(self, cmd="/help") -> Update:
        telegram_id = int(self.test_user.telegram_id or "")
        tg_user = TgUser(id=telegram_id, is_bot=False, first_name="Test")
        tg_chat = TgChat(id=12345, type="private")

        message = Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=tg_chat,
            from_user=tg_user,
            text=cmd,
            entities=(
                MessageEntity(type=MessageEntity.BOT_COMMAND, offset=0, length=len(cmd)),
            ),
        )

        update = Update(update_id=1, message=message)
        return update

    def _send_webhook_update(self, update: Update) -> requests.Response:
        """Retries on ConnectionRefused — the webhook server starts asynchronously."""
        webhook_url = f"http://{settings.TELEGRAM_BOT_WEBHOOK_HOST}:{settings.TELEGRAM_BOT_WEBHOOK_PORT}/{self.TELEGRAM_TOKEN_VALUE}"
        session = requests.Session()
        session.mount("http://", requests.adapters.HTTPAdapter(
            max_retries=urllib3.util.Retry(connect=5, backoff_factor=0.1),
        ))
        return session.post(webhook_url, json=update.to_dict(), timeout=5)

    def test_webhook_help_command(self):
        GET_ME_PATH = f"/bot{self.TELEGRAM_TOKEN_VALUE}/getMe"
        SEND_MESSAGE_PATH = f"/bot{self.TELEGRAM_TOKEN_VALUE}/sendMessage"

        # Find a free port for the webhook server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            webhook_port = s.getsockname()[1]

        with self.settings(
            DEBUG=False,
            TELEGRAM_BOT_WEBHOOK_HOST="127.0.0.1",
            TELEGRAM_BOT_WEBHOOK_PORT=webhook_port,
        ):
            self.server.expect_requests(
                [
                    ExpectedRequest(
                        Request("POST", GET_ME_PATH, {}),
                        self.GET_ME_RESPONSE,
                    ),
                    ExpectedRequest(
                        Request(
                            "POST",
                            SEND_MESSAGE_PATH,
                            {
                                "chat_id": "12345",
                                "text": bot.config.WELCOME_MESSAGE,
                                "parse_mode": "HTML",
                            },
                        ),
                        self.SEND_MESSAGE_RESPONSE,
                    ),
                ]
            )

            application = build_application()
            self._application = application
            self._start_application_in_thread(application, mode="webhook")

            response = self._send_webhook_update(self._create_command_update("/help"))
            self.assertIn(response.status_code, [200, 202, 204])

            self.assertTrue(
                self.server.wait_for_completion(timeout=5), "Bot did not send expected message"
            )
            self.server.check_requests()

    @override_settings(DEBUG=True)
    def test_polling_help_command(self):
        GET_ME_PATH = f"/bot{self.TELEGRAM_TOKEN_VALUE}/getMe"
        SEND_MESSAGE_PATH = f"/bot{self.TELEGRAM_TOKEN_VALUE}/sendMessage"
        GET_UPDATES_PATH = f"/bot{self.TELEGRAM_TOKEN_VALUE}/getUpdates"

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request("POST", GET_ME_PATH, {}),
                    self.GET_ME_RESPONSE,
                ),
                ExpectedRequest(
                    Request(
                        "POST",
                        GET_UPDATES_PATH,
                        {
                            "offset": "0",
                            "timeout": "10",
                        },
                    ),
                    json.dumps(
                        {
                            "ok": True,
                            "result": [self._create_command_update("/help").to_dict()],
                        }
                    ),
                ),
                ExpectedRequest(
                    Request(
                        "POST",
                        SEND_MESSAGE_PATH,
                        {
                            "chat_id": "12345",
                            "text": bot.config.WELCOME_MESSAGE,
                            "parse_mode": "HTML",
                        },
                    ),
                    self.SEND_MESSAGE_RESPONSE,
                ),
            ],
        )

        application = build_application()
        self._application = application
        self._start_application_in_thread(application, mode="polling")

        completed = self.server.wait_for_completion(timeout=5)
        self.assertTrue(completed, "Bot did not process all expected requests in time")

        self.server.check_requests()
