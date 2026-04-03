import asyncio
import json
import logging
import threading
import time
from unittest.mock import patch

from django.test import TestCase

from telegram import Bot, Update, Message, User as TgUser, Chat as TgChat

from helpdeskbot.help_desk_common import send_message, edit_message
from notifications.telegram.bot import SyncBot
from notifications.telegram.common import send_telegram_message, Chat
from notifications.telegram.tests import (
    BaseTelegramTest,
    MockTelegramServer,
    MockTelegramHandler,
    ExpectedRequest,
    Request,
    GET_ME_RESPONSE,
)


SEND_MESSAGE_RESPONSE = json.dumps({
    "ok": True,
    "result": {
        "message_id": 42,
        "date": int(time.time()),
        "chat": {"id": 12345, "type": "private"},
        "text": "ok",
        "from": {"id": 987654321, "is_bot": True, "first_name": "TestBot"},
    },
})

EDIT_MESSAGE_RESPONSE = json.dumps({
    "ok": True,
    "result": {
        "message_id": 42,
        "date": int(time.time()),
        "chat": {"id": 12345, "type": "private"},
        "text": "edited",
        "from": {"id": 987654321, "is_bot": True, "first_name": "TestBot"},
    },
})


def _create_mock_server(test_case):
    server = MockTelegramServer(
        test_case=test_case,
        server_address=("127.0.0.1", 0),
        RequestHandlerClass=MockTelegramHandler,
    )
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return server


class TestHelpdeskSendMessageAsync(TestCase):

    def _create_async_bot(self):
        self.server = _create_mock_server(self)
        server_port = self.server.server_address[1]
        bot = Bot(
            token=BaseTelegramTest.TOKEN,
            base_url=f"http://127.0.0.1:{server_port}/bot",
        )
        return bot

    def tearDown(self):
        if hasattr(self, "server"):
            self.server.shutdown()
            self.server.server_close()
        super().tearDown()

    def test_send_message_in_async_context(self):
        bot = self._create_async_bot()

        self.server.expect_requests([
            ExpectedRequest(
                Request("POST", BaseTelegramTest.GET_ME_PATH, {}),
                GET_ME_RESPONSE,
            ),
        ])

        async def _run():
            await bot.initialize()

            self.server.expect_requests([
                ExpectedRequest(
                    Request("POST", BaseTelegramTest.SEND_MESSAGE_PATH, {
                        "chat_id": "12345",
                        "text": "Hello from async",
                        "parse_mode": "HTML",
                        "link_preview_options": '{"is_disabled": true}',
                    }),
                    SEND_MESSAGE_RESPONSE,
                ),
            ])

            result = await send_message(bot, chat_id=12345, text="Hello from async")

            self.assertIsNotNone(result)
            self.assertEqual(result.message_id, 42)

        asyncio.run(_run())
        self.server.check_requests()

    def test_edit_message_in_async_context(self):
        bot = self._create_async_bot()

        self.server.expect_requests([
            ExpectedRequest(
                Request("POST", BaseTelegramTest.GET_ME_PATH, {}),
                GET_ME_RESPONSE,
            ),
        ])

        async def _run():
            await bot.initialize()

            edit_path = f"/bot{BaseTelegramTest.TOKEN}/editMessageText"
            self.server.expect_requests([
                ExpectedRequest(
                    Request("POST", edit_path, {
                        "chat_id": "12345",
                        "message_id": "42",
                        "text": "Edited text",
                        "parse_mode": "HTML",
                    }),
                    EDIT_MESSAGE_RESPONSE,
                ),
            ])

            result = await edit_message(bot, chat_id=12345, message_id=42, new_text="Edited text")

            self.assertIsNotNone(result)
            self.assertEqual(result.message_id, 42)

        asyncio.run(_run())
        self.server.check_requests()

    def test_send_message_via_update_get_bot(self):
        bot = self._create_async_bot()

        self.server.expect_requests([
            ExpectedRequest(
                Request("POST", BaseTelegramTest.GET_ME_PATH, {}),
                GET_ME_RESPONSE,
            ),
        ])

        async def _run():
            await bot.initialize()

            tg_user = TgUser(id=999, is_bot=False, first_name="Test")
            tg_chat = TgChat(id=12345, type="private")
            message = Message(
                message_id=1,
                date=None,
                chat=tg_chat,
                from_user=tg_user,
            )
            update = Update(update_id=1, message=message)
            update.set_bot(bot)

            self.server.expect_requests([
                ExpectedRequest(
                    Request("POST", BaseTelegramTest.SEND_MESSAGE_PATH, {
                        "chat_id": "12345",
                        "text": "Via update.get_bot()",
                        "parse_mode": "HTML",
                        "link_preview_options": '{"is_disabled": true}',
                    }),
                    SEND_MESSAGE_RESPONSE,
                ),
            ])

            got_bot = update.get_bot()
            result = await send_message(got_bot, chat_id=12345, text="Via update.get_bot()")

            self.assertIsNotNone(result)
            self.assertEqual(result.message_id, 42)

        asyncio.run(_run())
        self.server.check_requests()


class TestSyncBotFromAsyncContext(TestCase):

    def _create_sync_bot(self):
        self.server = _create_mock_server(self)
        server_port = self.server.server_address[1]

        sync_bot = SyncBot(
            token=BaseTelegramTest.TOKEN,
            base_url=f"http://127.0.0.1:{server_port}/bot",
        )

        self.server.expect_requests([
            ExpectedRequest(
                Request("POST", BaseTelegramTest.GET_ME_PATH, {}),
                GET_ME_RESPONSE,
            ),
        ])
        _ = sync_bot.bot
        self.server.wait_for_completion(timeout=5)
        self.server.remaining_expected_requests = None

        return sync_bot

    def tearDown(self):
        if hasattr(self, "server"):
            self.server.shutdown()
            self.server.server_close()
        super().tearDown()

    def test_sync_bot_works_inside_async_event_loop(self):
        sync_bot = self._create_sync_bot()

        async def _run():
            self.server.expect_requests([
                ExpectedRequest(
                    Request("POST", BaseTelegramTest.SEND_MESSAGE_PATH, {
                        "chat_id": "12345",
                        "text": "From async context",
                        "parse_mode": "HTML",
                        "link_preview_options": '{"is_disabled": true}',
                    }),
                    SEND_MESSAGE_RESPONSE,
                ),
            ])

            result = sync_bot.send_message(
                chat_id=12345,
                text="From async context",
                parse_mode="HTML",
                link_preview_options={"is_disabled": True},
            )
            self.assertIsNotNone(result)

        asyncio.run(_run())
        self.server.check_requests()


class TestSyncBotAfterFork(TestCase):

    def _create_sync_bot_with_server(self):
        self.server = _create_mock_server(self)
        server_port = self.server.server_address[1]

        sync_bot = SyncBot(
            token=BaseTelegramTest.TOKEN,
            base_url=f"http://127.0.0.1:{server_port}/bot",
        )
        return sync_bot

    def tearDown(self):
        if hasattr(self, "server"):
            self.server.shutdown()
            self.server.server_close()
        super().tearDown()

    def test_sends_message_after_simulated_fork(self):
        sync_bot = self._create_sync_bot_with_server()

        self.server.expect_requests([
            ExpectedRequest(
                Request("POST", BaseTelegramTest.GET_ME_PATH, {}),
                GET_ME_RESPONSE,
            ),
        ])
        _ = sync_bot.bot
        self.server.wait_for_completion(timeout=5)
        self.server.remaining_expected_requests = None

        sync_bot._owner_pid = -1

        self.server.expect_requests([
            ExpectedRequest(
                Request("POST", BaseTelegramTest.GET_ME_PATH, {}),
                GET_ME_RESPONSE,
            ),
            ExpectedRequest(
                Request("POST", BaseTelegramTest.SEND_MESSAGE_PATH, {
                    "chat_id": "12345",
                    "text": "After fork",
                    "parse_mode": "HTML",
                    "link_preview_options": '{"is_disabled": true}',
                }),
                SEND_MESSAGE_RESPONSE,
            ),
        ])

        with patch("notifications.telegram.common.bot", sync_bot):
            result = send_telegram_message(Chat(id=12345), "After fork")

        self.assertIsNotNone(result)
        self.assertEqual(result.message_id, 42)

    def test_logging_works_after_simulated_fork(self):
        sync_bot = self._create_sync_bot_with_server()

        self.server.expect_requests([
            ExpectedRequest(
                Request("POST", BaseTelegramTest.GET_ME_PATH, {}),
                GET_ME_RESPONSE,
            ),
        ])
        _ = sync_bot.bot
        self.server.wait_for_completion(timeout=5)
        self.server.remaining_expected_requests = None

        sync_bot._owner_pid = -1

        self.server.expect_requests([
            ExpectedRequest(
                Request("POST", BaseTelegramTest.GET_ME_PATH, {}),
                GET_ME_RESPONSE,
            ),
            ExpectedRequest(
                Request("POST", BaseTelegramTest.SEND_MESSAGE_PATH, {
                    "chat_id": "12345",
                    "text": "Log test",
                    "parse_mode": "HTML",
                    "link_preview_options": '{"is_disabled": true}',
                }),
                SEND_MESSAGE_RESPONSE,
            ),
        ])

        with self.assertLogs("notifications.telegram.common", level=logging.INFO) as cm:
            with patch("notifications.telegram.common.bot", sync_bot):
                send_telegram_message(Chat(id=12345), "Log test")

        self.assertTrue(
            any("sending message to chat_id 12345" in msg for msg in cm.output),
            f"Expected log line not found in: {cm.output}",
        )


class TestSyncBotInSyncContext(BaseTelegramTest, TestCase):

    def test_sync_bot_sends_message(self):
        test_chat = Chat(id=12345)

        self.server.expect_requests([
            ExpectedRequest(
                Request("POST", BaseTelegramTest.SEND_MESSAGE_PATH, {
                    "chat_id": "12345",
                    "text": "Sync context message",
                    "parse_mode": "HTML",
                    "link_preview_options": '{"is_disabled": true}',
                }),
                SEND_MESSAGE_RESPONSE,
            ),
        ])

        result = send_telegram_message(test_chat, "Sync context message")

        self.assertIsNotNone(result)
        self.assertEqual(result.message_id, 42)

    def test_sync_bot_consecutive_calls(self):
        """Consecutive calls work — verifies persistent event loop doesn't close between calls."""
        test_chat = Chat(id=12345)

        self.server.expect_requests([
            ExpectedRequest(
                Request("POST", BaseTelegramTest.SEND_MESSAGE_PATH, {
                    "chat_id": "12345",
                    "text": "First sync call",
                    "parse_mode": "HTML",
                    "link_preview_options": '{"is_disabled": true}',
                }),
                SEND_MESSAGE_RESPONSE,
            ),
            ExpectedRequest(
                Request("POST", BaseTelegramTest.SEND_MESSAGE_PATH, {
                    "chat_id": "12345",
                    "text": "Second sync call",
                    "parse_mode": "HTML",
                    "link_preview_options": '{"is_disabled": true}',
                }),
                SEND_MESSAGE_RESPONSE,
            ),
        ])

        first = send_telegram_message(test_chat, "First sync call")
        self.assertIsNotNone(first)

        second = send_telegram_message(test_chat, "Second sync call")
        self.assertIsNotNone(second)
