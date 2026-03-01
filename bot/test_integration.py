"""
Integration tests for the Telegram bot.

Uses a mock Telegram API server (BaseTelegramTest) with real bot main(),
real Update objects, and actual HTTP requests to the webhook server.
"""

import contextlib
import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import patch

import django
from django.conf import settings
from django.test import TestCase, override_settings
import django.db

from bot.main import start_server, Server
import bot.config

django.setup()

import requests
import urllib3
import telegram
from telegram import Update, Message, User as TgUser, Chat as TgChat

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

    bot_server: Server | None

    def setUp(self):
        super().setUp()

        server_port = self.server.server_address[1]
        telegram_base_url = f"http://127.0.0.1:{server_port}/"

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

        # Prevent 'connection is closed' errors — Django closes DB connections between requests,
        # but bot handler threads reuse them
        self.close_old_connections_patch = patch(
            "bot.handlers.common.close_old_connections"
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

        self.bot_server = None

    def tearDown(self):
        if self.bot_server:
            self.bot_server.stop()

        self.test_user.delete()
        self.close_old_connections_patch.stop()
        self.settings_override.disable()

        # Shut down bot_server first, then the mock API (in super()),
        # otherwise the polling bot keeps hitting a dead server
        super().tearDown()

    def _create_update(
        self, message_text: str, reply_to_text: Optional[str] = None
    ) -> Update:
        telegram_id = int(self.test_user.telegram_id or "")
        tg_user = TgUser(id=telegram_id, is_bot=False, first_name="Test")
        tg_chat = TgChat(id=12345, type="private")

        message = Message(
            message_id=1,
            date=int(time.time()),
            chat=tg_chat,
            from_user=tg_user,
            text=message_text,
            bot=self.bot,
        )

        if reply_to_text:
            reply_message = Message(
                message_id=0,
                date=int(time.time()),
                chat=tg_chat,
                text=reply_to_text,
                bot=self.bot,
                from_user=telegram.User(id=6789, is_bot=False, first_name="First"),
            )
            message.reply_to_message = reply_message

        update = Update(update_id=1, message=message, entities=123)
        return update

    def _create_command_update(self, cmd="/help") -> Update:
        update = self._create_update(cmd)
        assert isinstance(update.message, Message)
        update.message.entities.append(
            telegram.MessageEntity(type="bot_command", offset=0, length=len(cmd))
        )
        return update

    def _send_webhook_update(self, update: Update) -> requests.Response:
        """Retries on ConnectionRefused — the webhook server starts asynchronously."""
        webhook_url = f"http://{settings.TELEGRAM_BOT_WEBHOOK_HOST}:{settings.TELEGRAM_BOT_WEBHOOK_PORT}/{self.TELEGRAM_TOKEN_VALUE}"
        session = requests.Session()
        session.mount("http://", requests.adapters.HTTPAdapter(
            max_retries=urllib3.util.Retry(connect=5, backoff_factor=0.1),
        ))
        return session.post(webhook_url, json=update.to_dict(), timeout=5)

    @override_settings(DEBUG=False)
    def test_webhook_help_command(self):
        SEND_MESSAGE_PATH = f"/{self.TELEGRAM_TOKEN_VALUE}/sendMessage"

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "GET",
                        f"/{self.TELEGRAM_TOKEN_VALUE}/getMe",
                        {},
                    ),
                    self.GET_ME_RESPONSE,
                ),
                ExpectedRequest(
                    Request(
                        "POST",
                        f"/{self.TELEGRAM_TOKEN_VALUE}/setWebhook",
                        {
                            "url": settings.TELEGRAM_BOT_WEBHOOK_URL
                            + self.TELEGRAM_TOKEN_VALUE,
                            "max_connections": "40",
                        },
                    ),
                    self.SET_WEBHOOK_RESPONSE,
                ),
                ExpectedRequest(
                    Request(
                        "POST",
                        SEND_MESSAGE_PATH,
                        {
                            "chat_id": "12345",
                            "text": bot.config.WELCOME_MESSAGE,
                            "parse_mode": "HTML",
                            "disable_notification": "False",
                        },
                    ),
                    self.SEND_MESSAGE_RESPONSE,
                ),
            ]
        )

        self.bot_server = start_server()

        response = self._send_webhook_update(self._create_command_update("/help"))
        self.assertIn(response.status_code, [200, 202, 204])

        self.assertTrue(
            self.server.wait_for_completion(timeout=5), "Bot did not send expected message"
        )
        self.server.check_requests()

    @override_settings(DEBUG=True)
    def test_polling_help_command(self):
        SEND_MESSAGE_PATH = f"/{self.TELEGRAM_TOKEN_VALUE}/sendMessage"
        GET_UPDATES_PATH = f"/{self.TELEGRAM_TOKEN_VALUE}/getUpdates"

        # sendMessage and getUpdates race between the dispatcher and polling threads,
        # so request order is non-deterministic — matching is content-based
        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "GET",
                        f"/{self.TELEGRAM_TOKEN_VALUE}/getMe",
                        {},
                    ),
                    self.GET_ME_RESPONSE,
                ),
                ExpectedRequest(
                    Request(
                        "POST",
                        f"/{self.TELEGRAM_TOKEN_VALUE}/deleteWebhook",
                        {},
                    ),
                    self.SET_WEBHOOK_RESPONSE,
                ),
                ExpectedRequest(
                    Request(
                        "POST",
                        GET_UPDATES_PATH,
                        {
                            "limit": "100",
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
                            "disable_notification": "False",
                        },
                    ),
                    self.SEND_MESSAGE_RESPONSE,
                ),
            ],
        )

        self.bot_server = start_server()

        completed = self.server.wait_for_completion(timeout=5)
        self.assertTrue(completed, "Bot did not process all expected requests in time")

        self.server.check_requests()
