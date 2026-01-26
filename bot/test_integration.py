"""
Integration tests for the Telegram bot.

Tests the bot with real Telegram library calls (no mocking of telegram lib), using:
- Mock Telegram API server (from BaseTelegramTest)
- Real bot main() function running in webhook/polling mode
- Real Update objects created by telegram library
- Actual HTTP requests to webhook server
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
import telegram
from telegram import Update, Message, User as TgUser, Chat as TgChat

from notifications.telegram.tests import BaseTelegramTest, ExpectedRequest, Request
from users.models.user import User

log = logging.getLogger(__name__)


class BotIntegrationTest(BaseTelegramTest, TestCase):
    """Integration tests for bot webhook and polling - runs real main()"""

    tags = {"telegram", "telegram_bot", "telegram_integration"}

    # Use the same TOKEN as BaseTelegramTest
    TELEGRAM_TOKEN_VALUE = BaseTelegramTest.TOKEN

    # Telegram API responses
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

        # Calculate the mock server base URL dynamically
        server_port = self.server.server_address[1]
        telegram_base_url = f"http://127.0.0.1:{server_port}/"

        # Create test user with active membership
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

        # Patch close_old_connections to prevent 'connection is closed' errors in tests
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

        # Clean up
        self.test_user.delete()
        self.close_old_connections_patch.stop()
        self.settings_override.disable()

        # NB: shut down bot_server first, then the API (in super()):
        # in the polling mode, bot polls the API endlessly and fails with a gnarly stacktrace otherwise
        super().tearDown()

    def _create_update(
        self, message_text: str, reply_to_text: Optional[str] = None
    ) -> Update:
        """Create a real Update object using telegram library"""
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
        """
        Send an update to the webhook server via HTTP POST.
        """
        webhook_url = f"http://{settings.TELEGRAM_BOT_WEBHOOK_HOST}:{settings.TELEGRAM_BOT_WEBHOOK_PORT}/{self.TELEGRAM_TOKEN_VALUE}"
        update_dict = update.to_dict()
        try:
            response = requests.post(webhook_url, json=update_dict, timeout=5)
            return response
        except Exception as e:
            log.error(f"Failed to send webhook update: {e}")
            raise

    @override_settings(DEBUG=False)
    def test_webhook_help_command(self):
        """
        Test: Send /help command via webhook and verify bot sends help message

        Integration flow:
        1. Start bot in webhook mode (DEBUG=False)
        2. Send /help update via HTTP to webhook endpoint
        3. Verify bot calls Telegram API sendMessage
        """
        # Setup expected Telegram API calls
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

        # Wait for bot to process the update
        time.sleep(1)

        # Verify expected API calls were made
        self.server.check_requests()

    @override_settings(DEBUG=True)
    def test_polling_help_command(self):
        """
        Test: Send /help command via polling and verify bot sends help message

        Integration flow:
        1. Start bot in polling mode (DEBUG=True)
        2. Send /help update via Telegram API response
        3. Verify bot calls Telegram API sendMessage
        """
        # Setup expected Telegram API calls
        SEND_MESSAGE_PATH = f"/{self.TELEGRAM_TOKEN_VALUE}/sendMessage"

        # HACK: this relies on weird timings and sleeps to get things to work properly:
        # first, a getUpdates call returns the single update;
        # while this is being processed through a queue, another getUpdates call sleeps for a short time
        # and then returns nothing;
        # while it sleeps, in another client thread, the bot sends its sendMessage that is checked against
        # the 'expected' instance;
        # finally, the third getUpdates call sleeps for a longer while before returning nothing;
        # we expect that during that time the test will shut down and no further getUpdates calls will be made
        #
        # it would be more robust to make API handlers stateful, implementing a mechanism that returns the single
        # update instantly and then however many empty results would be necessary, sleeping for 100ms each time
        # to conserve some CPU
        #
        # that would require an involved refactoring however, so only worthwhile whenever the server logic
        # is undergoing constant change -- that would require this test suite to catch any problems;
        # otherwise, in case the performance here with sleeps becomes a problem, it would be better
        # to mark this test in such a way that it's only ran when specifically requested
        # or to simply remove it
        #
        # the original intent was to write these tests, upgrade the Telegram library written by the Olympian athletes
        # without any regard to backwards compatibility, and use them to try and ensure nothing breaks;
        # this entire exercise can be repeated as often as such an upgrade is needed, including vibecoding
        # the tests once again -- the author very much hopes that the foundational models would get better
        # in the meantime to allow this to be done unsupervised
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
                        f"/{self.TELEGRAM_TOKEN_VALUE}/getUpdates",
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
                        f"/{self.TELEGRAM_TOKEN_VALUE}/getUpdates",
                        {
                            "limit": "100",
                            "offset": "2",
                            "timeout": "10",
                        },
                    ),
                    json.dumps({"ok": True, "result": []}),
                    wait=0.2,
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
                ExpectedRequest(
                    Request(
                        "POST",
                        f"/{self.TELEGRAM_TOKEN_VALUE}/getUpdates",
                        {
                            "limit": "100",
                            "offset": "2",
                            "timeout": "10",
                        },
                    ),
                    json.dumps({"ok": True, "result": []}),
                    wait=1,
                ),
            ]
        )

        self.bot_server = start_server()

        # response = self._send_webhook_update(self._create_command_update("/help"))
        # self.assertIn(response.status_code, [200, 202, 204])

        # Wait for bot to process the update
        time.sleep(1)

        # Verify expected API calls were made
        self.server.check_requests()
