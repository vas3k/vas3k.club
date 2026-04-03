import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import patch, MagicMock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "club.settings")
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

import django
django.setup()

from django.test import TransactionTestCase
from telegram import Update, Message, User as TgUser, Chat as TgChat

from bot.handlers.llm import llm_response
from notifications.telegram.tests import BaseTelegramTest, ExpectedRequest, Request
from users.models.user import User


class LLMResponseTest(BaseTelegramTest, TransactionTestCase):
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

    SEND_MESSAGE_PATH = f"/bot{BaseTelegramTest.TOKEN}/sendMessage"
    SEND_CHAT_ACTION_PATH = f"/bot{BaseTelegramTest.TOKEN}/sendChatAction"

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

    def tearDown(self):
        super().tearDown()

    def _create_update(
        self, message_text: str, reply_to_text: Optional[str] = None
    ) -> Update:
        """Create a test Update object"""
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
            reply_to_message.set_bot(self.sync_bot.bot)

        message = Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=tg_chat,
            from_user=tg_user,
            text=message_text,
            reply_to_message=reply_to_message,
        )
        message.set_bot(self.sync_bot.bot)
        update = Update(update_id=1, message=message)
        return update

    @patch("bot.handlers.llm.ask_assistant")
    def test_simple_message(self, mock_ask_assistant):
        """Test handling a simple message"""
        mock_ask_assistant.return_value = "This is a test response"

        update = self._create_update("Hello bot")
        context = MagicMock()
        context.bot = self.sync_bot.bot

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
                            "link_preview_options": '{"is_disabled": true}',
                        },
                    ),
                    self.RESPONSE,
                ),
            ]
        )

        asyncio.run(llm_response(update, context))

        mock_ask_assistant.assert_called_once()
        call_args = mock_ask_assistant.call_args[0][0]
        self.assertIn("Test User", call_args)
        self.assertIn("Hello bot", call_args)

    @patch("bot.handlers.llm.ask_assistant")
    def test_message_with_reply(self, mock_ask_assistant):
        """Test message with reply_to_message"""
        mock_ask_assistant.return_value = "Replied to previous message"

        update = self._create_update(
            "What about this?", reply_to_text="Previous message"
        )
        context = MagicMock()
        context.bot = self.sync_bot.bot

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
                            "link_preview_options": '{"is_disabled": true}',
                        },
                    ),
                    self.RESPONSE,
                ),
            ]
        )

        asyncio.run(llm_response(update, context))

        call_args = mock_ask_assistant.call_args[0][0]
        self.assertIn("Previous message", call_args)

    @patch("bot.handlers.llm.ask_assistant")
    def test_inactive_user(self, mock_ask_assistant):
        """Test that inactive users get rejected"""
        # Make user inactive by setting membership to expired
        self.test_user.membership_expires_at = datetime.now(timezone.utc) - timedelta(
            days=1
        )
        self.test_user.save()

        update = self._create_update("Hello bot")
        context = MagicMock()
        context.bot = self.sync_bot.bot

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        self.SEND_MESSAGE_PATH,
                        {
                            "chat_id": "12345",
                            "text": "🙈 Я отвечаю только чувакам с активной подпиской в Клубе. Иди продлевай! https://vas3k.club/user/me/",
                            "link_preview_options": '{"is_disabled": true}',
                        },
                    ),
                    self.RESPONSE,
                )
            ]
        )

        asyncio.run(llm_response(update, context))

        # Should NOT call assistant for inactive user
        mock_ask_assistant.assert_not_called()

    @patch("bot.handlers.llm.is_rate_limited")
    @patch("bot.handlers.llm.ask_assistant")
    def test_rate_limited(self, mock_ask_assistant, mock_rate_limited):
        """Test rate limiting response"""
        mock_rate_limited.return_value = True

        update = self._create_update("Hello bot")
        context = MagicMock()
        context.bot = self.sync_bot.bot

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
                        },
                    ),
                    self.RESPONSE,
                ),
            ]
        )

        asyncio.run(llm_response(update, context))

        mock_ask_assistant.assert_not_called()

    @patch("bot.handlers.llm.ask_assistant")
    def test_message_with_caption(self, mock_ask_assistant):
        """Test handling a message with caption instead of text"""
        mock_ask_assistant.return_value = "Response to caption"

        telegram_id = int(self.test_user.telegram_id or "")
        tg_user = TgUser(id=telegram_id, is_bot=False, first_name="Test")
        tg_chat = TgChat(id=12345, type="private")

        message = Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=tg_chat,
            from_user=tg_user,
            caption="Image caption text",
        )
        message.set_bot(self.sync_bot.bot)

        update = Update(update_id=1, message=message)
        context = MagicMock()
        context.bot = self.sync_bot.bot

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
                            "link_preview_options": '{"is_disabled": true}',
                        },
                    ),
                    self.RESPONSE,
                ),
            ]
        )

        asyncio.run(llm_response(update, context))

        mock_ask_assistant.assert_called_once()
        call_args = mock_ask_assistant.call_args[0][0]
        self.assertIn("Image caption text", call_args)

    @patch("bot.handlers.llm.ask_assistant")
    def test_empty_message(self, mock_ask_assistant):
        """Test that empty messages are ignored"""
        telegram_id = int(self.test_user.telegram_id or "")
        tg_user = TgUser(id=telegram_id, is_bot=False, first_name="Test")
        tg_chat = TgChat(id=12345, type="private")

        message = Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=tg_chat,
            from_user=tg_user,
        )
        message.set_bot(self.sync_bot.bot)

        update = Update(update_id=1, message=message)
        context = MagicMock()
        context.bot = self.sync_bot.bot

        asyncio.run(llm_response(update, context))

        mock_ask_assistant.assert_not_called()

    @patch("bot.handlers.llm.ask_assistant")
    def test_long_response(self, mock_ask_assistant):
        """Test handling a long multi-paragraph response from assistant"""
        mock_ask_assistant.return_value = "First paragraph\n\nSecond paragraph\n\nThird paragraph"
        update = self._create_update("Tell me a story")
        context = MagicMock()
        context.bot = self.sync_bot.bot

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
                            "link_preview_options": '{"is_disabled": true}',
                        },
                    ),
                    self.RESPONSE,
                ),
            ]
        )

        asyncio.run(llm_response(update, context))

        mock_ask_assistant.assert_called_once()

    @patch("bot.handlers.llm.ask_assistant")
    def test_assistant_error_sends_fallback_message(self, mock_ask_assistant):
        mock_ask_assistant.side_effect = Exception("OpenAI API error")

        update = self._create_update("Hello bot")
        context = MagicMock()
        context.bot = self.sync_bot.bot

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
                            "text": "Что-то сломалось, попробуй ещё раз позже 🤷",
                        },
                    ),
                    self.RESPONSE,
                ),
            ]
        )

        asyncio.run(llm_response(update, context))

        self.assertTrue(self.server.wait_for_completion(timeout=5))
