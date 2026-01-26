import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import patch, MagicMock

import django
from django.test import TestCase
from telegram import Update, Message, User as TgUser, Chat as TgChat
import telegram
from telegram.ext import CallbackContext

from bot.handlers.llm import llm_response
from notifications.telegram.tests import BaseTelegramTest, ExpectedRequest, Request
from users.models.user import User

django.setup()

log = logging.getLogger(__name__)


class LLMResponseTest(BaseTelegramTest, TestCase):
    """Test the llm_response handler with mock Telegram server"""

    tags = {"telegram", "telegram_bot", "telegram_handler"}

    RESPONSE = json.dumps(
        {
            "ok": True,
            "result": {
                "message_id": 123456,
                "date": int(time.time()),
                "chat": {"id": 12345, "type": "private"},
            },
        }
    )

    CHAT_ACTION_RESPONSE = json.dumps({"ok": True, "result": True})

    SEND_MESSAGE_PATH = f"/{BaseTelegramTest.TOKEN}/sendMessage"
    SEND_CHAT_ACTION_PATH = f"/{BaseTelegramTest.TOKEN}/sendChatAction"

    def setUp(self):
        super().setUp()
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

        # HACK: the hack in bot.handlers.common.get_club_user() causes 'connection is closed' errors in tests,
        # this is a work-around
        self.close_old_connections_patch = patch(
            "bot.handlers.common.close_old_connections"
        )
        self.close_old_connections_patch.start()

    def tearDown(self):
        super().tearDown()
        self.test_user.delete()
        self.close_old_connections_patch.stop()

    def _create_update(
        self, message_text: str, reply_to_text: Optional[str] = None
    ) -> Update:
        """Create a test Update object"""
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

        update = Update(update_id=1, message=message)
        return update

    @patch("bot.handlers.llm.ask_assistant")
    def test_simple_message(self, mock_ask_assistant):
        """Test handling a simple message"""
        mock_ask_assistant.return_value = ["This is a test response"]

        update = self._create_update("Hello bot")
        context = MagicMock(spec=CallbackContext)
        context.bot = self.bot  # Get the mocked bot

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        self.SEND_CHAT_ACTION_PATH,
                        {
                            "chat_id": "12345",
                            "action": "typing",
                        },
                    ),
                    self.CHAT_ACTION_RESPONSE,
                ),
                ExpectedRequest(
                    Request(
                        "POST",
                        self.SEND_MESSAGE_PATH,
                        {
                            "chat_id": "12345",
                            "text": "This is a test response",
                            "parse_mode": "HTML",
                            "disable_web_page_preview": "True",
                            "disable_notification": "False",
                        },
                    ),
                    self.RESPONSE,
                ),
            ]
        )

        llm_response(update, context)

        mock_ask_assistant.assert_called_once()
        call_args = mock_ask_assistant.call_args[0][0]
        assert "Test User" in call_args
        assert "Hello bot" in call_args

    @patch("bot.handlers.llm.ask_assistant")
    def test_message_with_reply(self, mock_ask_assistant):
        """Test message with reply_to_message"""
        mock_ask_assistant.return_value = ["Replied to previous message"]

        update = self._create_update(
            "What about this?", reply_to_text="Previous message"
        )
        context = MagicMock(spec=CallbackContext)
        context.bot = self.bot

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        self.SEND_CHAT_ACTION_PATH,
                        {
                            "chat_id": "12345",
                            "action": "typing",
                        },
                    ),
                    self.CHAT_ACTION_RESPONSE,
                ),
                ExpectedRequest(
                    Request(
                        "POST",
                        self.SEND_MESSAGE_PATH,
                        {
                            "chat_id": "12345",
                            "text": "Replied to previous message",
                            "parse_mode": "HTML",
                            "disable_web_page_preview": "True",
                            "disable_notification": "False",
                        },
                    ),
                    self.RESPONSE,
                ),
            ]
        )

        llm_response(update, context)

        call_args = mock_ask_assistant.call_args[0][0]
        assert "Previous message" in call_args

    @patch("bot.handlers.llm.ask_assistant")
    def test_inactive_user(self, mock_ask_assistant):
        """Test that inactive users get rejected"""
        # Make user inactive by setting membership to expired
        self.test_user.membership_expires_at = datetime.now(timezone.utc) - timedelta(
            days=1
        )
        self.test_user.save()

        update = self._create_update("Hello bot")
        context = MagicMock(spec=CallbackContext)
        context.bot = self.bot

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        self.SEND_MESSAGE_PATH,
                        {
                            "chat_id": "12345",
                            "text": "🙈 Я отвечаю только чувакам с активной подпиской в Клубе. Иди продлевай! https://vas3k.club/user/me/",
                            "disable_web_page_preview": "True",
                            "disable_notification": "False",
                        },
                    ),
                    self.RESPONSE,
                )
            ]
        )

        llm_response(update, context)

        # Should NOT call assistant for inactive user
        mock_ask_assistant.assert_not_called()

    @patch("bot.handlers.llm.is_rate_limited")
    @patch("bot.handlers.llm.ask_assistant")
    def test_rate_limited(self, mock_ask_assistant, mock_rate_limited):
        """Test rate limiting response"""
        mock_rate_limited.return_value = True

        update = self._create_update("Hello bot")
        context = MagicMock(spec=CallbackContext)
        context.bot = self.bot

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        self.SEND_CHAT_ACTION_PATH,
                        {
                            "chat_id": "12345",
                            "action": "typing",
                        },
                    ),
                    self.CHAT_ACTION_RESPONSE,
                ),
                ExpectedRequest(
                    Request(
                        "POST",
                        self.SEND_MESSAGE_PATH,
                        {
                            "chat_id": "12345",
                            "text": "Чот я устал отвечать на вопросы... давай потом",
                            "disable_notification": "False",
                        },
                    ),
                    self.RESPONSE,
                ),
            ]
        )

        llm_response(update, context)

        mock_ask_assistant.assert_not_called()

    @patch("bot.handlers.llm.ask_assistant")
    def test_message_with_caption(self, mock_ask_assistant):
        """Test handling a message with caption instead of text"""
        mock_ask_assistant.return_value = ["Response to caption"]

        telegram_id = int(self.test_user.telegram_id or "")
        tg_user = TgUser(id=telegram_id, is_bot=False, first_name="Test")
        tg_chat = TgChat(id=12345, type="private")

        message = Message(
            message_id=1,
            date=int(time.time()),
            chat=tg_chat,
            from_user=tg_user,
            caption="Image caption text",
            bot=self.bot,
        )

        update = Update(update_id=1, message=message)
        context = MagicMock(spec=CallbackContext)
        context.bot = self.bot

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        self.SEND_CHAT_ACTION_PATH,
                        {
                            "chat_id": "12345",
                            "action": "typing",
                        },
                    ),
                    self.CHAT_ACTION_RESPONSE,
                ),
                ExpectedRequest(
                    Request(
                        "POST",
                        self.SEND_MESSAGE_PATH,
                        {
                            "chat_id": "12345",
                            "text": "Response to caption",
                            "parse_mode": "HTML",
                            "disable_web_page_preview": "True",
                            "disable_notification": "False",
                        },
                    ),
                    self.RESPONSE,
                ),
            ]
        )

        llm_response(update, context)

        mock_ask_assistant.assert_called_once()
        call_args = mock_ask_assistant.call_args[0][0]
        assert "Image caption text" in call_args

    @patch("bot.handlers.llm.ask_assistant")
    def test_empty_message(self, mock_ask_assistant):
        """Test that empty messages are ignored"""
        telegram_id = int(self.test_user.telegram_id or "")
        tg_user = TgUser(id=telegram_id, is_bot=False, first_name="Test")
        tg_chat = TgChat(id=12345, type="private")

        message = Message(
            message_id=1,
            date=int(time.time()),
            chat=tg_chat,
            from_user=tg_user,
            bot=self.bot,
        )

        update = Update(update_id=1, message=message)
        context = MagicMock(spec=CallbackContext)
        context.bot = self.bot

        llm_response(update, context)

        mock_ask_assistant.assert_not_called()

    @patch("bot.handlers.llm.ask_assistant")
    def test_multiple_responses(self, mock_ask_assistant):
        """Test handling multiple response lines from assistant"""
        mock_ask_assistant.return_value = [
            "First paragraph",
            "Second paragraph",
            "Third paragraph",
        ]
        update = self._create_update("Tell me a story")
        context = MagicMock(spec=CallbackContext)
        context.bot = self.bot

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        self.SEND_CHAT_ACTION_PATH,
                        {
                            "chat_id": "12345",
                            "action": "typing",
                        },
                    ),
                    self.CHAT_ACTION_RESPONSE,
                ),
                ExpectedRequest(
                    Request(
                        "POST",
                        self.SEND_MESSAGE_PATH,
                        {
                            "chat_id": "12345",
                            "text": "First paragraph\n\nSecond paragraph\n\nThird paragraph",
                            "parse_mode": "HTML",
                            "disable_web_page_preview": "True",
                            "disable_notification": "False",
                        },
                    ),
                    self.RESPONSE,
                ),
            ]
        )

        llm_response(update, context)

        mock_ask_assistant.assert_called_once()
