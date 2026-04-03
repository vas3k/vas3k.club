import email.parser
import email.policy
from dataclasses import dataclass
import json
import http.server

import socketserver
import threading
import time
from typing import Any, Protocol
from unittest.mock import patch
from urllib.parse import parse_qsl

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

import django
from django.test import TestCase

from notifications.telegram.bot import SyncBot
from notifications.telegram.common import (
    send_telegram_message,
    send_telegram_image,
    Chat,
)
django.setup()

GET_ME_RESPONSE = json.dumps({
    "ok": True,
    "result": {
        "id": 987654321,
        "is_bot": True,
        "first_name": "TestBot",
        "username": "test_bot",
    },
})


@dataclass
class Request:
    method: str
    path: str
    body: dict[str, str]


@dataclass
class ExpectedRequest:
    request: Request
    response: str


class MockTelegramHandler(http.server.BaseHTTPRequestHandler):
    test_case: TestCase

    def _do_handle(self, request):
        server = self._get_server()

        if server.remaining_expected_requests is None:
            raise RuntimeError("expect_requests not called")

        for i, expected in enumerate(server.remaining_expected_requests):
            if request == expected.request:
                server.remaining_expected_requests.pop(i)
                server._notify_if_complete()
                self._send_json(expected.response)
                return

        self._send_json('{"ok": true, "result": []}')

    def _send_json(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        content_type = self.headers.get("Content-Type", "")

        request = Request(
            path=self.path,
            method=self.command,
            body=self._parse_body(body, content_type),
        )
        self._do_handle(request)

    def _parse_body(self, body: bytes, content_type: str) -> dict:
        if not body:
            return {}
        if "application/json" in content_type:
            return json.loads(body.decode("utf-8"))
        if "multipart/form-data" in content_type:
            return self._parse_multipart(body, content_type)
        return dict(parse_qsl(body.decode("utf-8"), keep_blank_values=True))

    def _parse_multipart(self, body: bytes, content_type: str) -> dict:
        raw = f"Content-Type: {content_type}\r\n\r\n".encode() + body
        msg = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(raw)
        result = {}
        for part in msg.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if name:
                result[name] = part.get_content()
        return result

    def do_GET(self):
        request = Request(
            path=self.path,
            method="GET",
            body={},
        )

        self._do_handle(request)

    def _get_server(self):
        server = self.server
        if not isinstance(server, MockTelegramServer):
            raise RuntimeError(f"unexpected server class: {server.__class__}")

        return server


class TelegramTestCaseProtocol(Protocol):
    server: "MockTelegramServer"
    sync_bot: SyncBot
    patcher: Any

    def setUp(self) -> None: ...
    def tearDown(self) -> None: ...
    def assertTrue(self, expr, msg=None): ...
    def fail(self, msg=None): ...


class MockTelegramServer(socketserver.TCPServer):
    test_case: TelegramTestCaseProtocol
    remaining_expected_requests: list[ExpectedRequest] | None = None
    all_expected_done: threading.Event

    def __init__(self, test_case: TelegramTestCaseProtocol, *args, **kwargs) -> None:
        self.test_case = test_case
        self.all_expected_done = threading.Event()
        super().__init__(*args, **kwargs)

    def expect_requests(self, expected_requests: list[ExpectedRequest]):
        self.remaining_expected_requests = expected_requests
        self.all_expected_done = threading.Event()

        if not expected_requests:
            self.all_expected_done.set()

    def wait_for_completion(self, timeout=5):
        return self.all_expected_done.wait(timeout=timeout)

    def _notify_if_complete(self):
        if not self.remaining_expected_requests:
            self.all_expected_done.set()

    def check_requests(self):
        self.test_case.assertTrue(
            self.remaining_expected_requests is None
            or len(self.remaining_expected_requests) == 0,
            f"some requests not executed: {self.remaining_expected_requests}",
        )


class BaseTelegramTest:
    tags = ["telegram"]

    TOKEN = "123456789:ABCDefGhijklmnOpqrstuvWxyzAbcdefghijk"
    GET_ME_PATH = f"/bot{TOKEN}/getMe"
    SEND_MESSAGE_PATH = f"/bot{TOKEN}/sendMessage"
    SEND_PHOTO_PATH = f"/bot{TOKEN}/sendPhoto"

    def setUp(self: TelegramTestCaseProtocol):
        self.server = MockTelegramServer(
            test_case=self,
            server_address=("127.0.0.1", 0),
            RequestHandlerClass=MockTelegramHandler,
        )

        server_port = self.server.server_address[1]
        server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        server_thread.start()

        self.sync_bot = SyncBot(
            Bot(
                token=BaseTelegramTest.TOKEN,
                base_url=f"http://127.0.0.1:{server_port}/bot",
            )
        )

        self.server.expect_requests([
            ExpectedRequest(
                Request("POST", BaseTelegramTest.GET_ME_PATH, {}),
                GET_ME_RESPONSE,
            ),
        ])
        _ = self.sync_bot.bot
        self.server.wait_for_completion(timeout=5)
        self.server.remaining_expected_requests = None

        self.patcher = patch("notifications.telegram.common.bot", self.sync_bot)
        self.patcher.start()

        super().setUp()

    def tearDown(self: TelegramTestCaseProtocol) -> None:
        super().tearDown()

        self.patcher.stop()
        self.server.shutdown()
        self.server.server_close()
        self.server.check_requests()


class SendTelegramMessageTest(BaseTelegramTest, TestCase):
    MESSAGE_BODY_TEMPLATE = {
        "chat_id": "12345",
        "parse_mode": "HTML",
        "link_preview_options": '{"is_disabled": true}',
    }

    MESSAGE_BODY_TEMPLATE_WITH_PREVIEW = {
        k: v
        for k, v in MESSAGE_BODY_TEMPLATE.items()
        if k != "link_preview_options"
    }

    RESPONSE = json.dumps(
        {
            "ok": True,
            "result": {
                "message_id": 123456,
                "date": int(time.time()),
                "chat": {
                    "id": 12345,
                    "type": "private",
                },
            },
        }
    )

    test_chat = Chat(id=12345)

    def test_send_telegram_message_text(self):
        """Test sending a simple text message"""
        text = "Hello, Telegram!"

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        SendTelegramMessageTest.SEND_MESSAGE_PATH,
                        {
                            **SendTelegramMessageTest.MESSAGE_BODY_TEMPLATE,
                            "text": "Hello, Telegram!",
                        },
                    ),
                    SendTelegramMessageTest.RESPONSE,
                )
            ]
        )

        send_telegram_message(self.test_chat, text)

    def test_send_telegram_message_truncation(self):
        """Test that messages longer than NORMAL_TEXT_LIMIT are truncated"""
        long_text = "A" * 5000
        truncated_text = "A" * 4096

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        SendTelegramMessageTest.SEND_MESSAGE_PATH,
                        {
                            **SendTelegramMessageTest.MESSAGE_BODY_TEMPLATE,
                            "text": truncated_text,
                        },
                    ),
                    SendTelegramMessageTest.RESPONSE,
                )
            ]
        )

        send_telegram_message(self.test_chat, long_text)

    def test_send_telegram_message_with_image(self):
        """Test sending a message with an embedded image"""
        text = "Check this: https://example.com/image.jpg"

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        SendTelegramMessageTest.SEND_PHOTO_PATH,
                        {
                            **SendTelegramMessageTest.MESSAGE_BODY_TEMPLATE_WITH_PREVIEW,
                            "photo": "https://example.com/image.jpg",
                            "caption": text,
                        },
                    ),
                    SendTelegramMessageTest.RESPONSE,
                )
            ]
        )

        send_telegram_message(self.test_chat, text)

    def test_send_telegram_message_parse_mode(self):
        """Test that parse_mode is sent in the request"""
        text = "Hello"

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        SendTelegramMessageTest.SEND_MESSAGE_PATH,
                        {
                            **SendTelegramMessageTest.MESSAGE_BODY_TEMPLATE,
                            "text": text,
                            "parse_mode": "Markdown",
                        },
                    ),
                    SendTelegramMessageTest.RESPONSE,
                )
            ]
        )

        send_telegram_message(
            self.test_chat, text, parse_mode="Markdown"
        )

    def test_send_telegram_message_enable_preview(self):
        """Test that disable_preview flag is sent correctly"""
        text = "Hello"

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        SendTelegramMessageTest.SEND_MESSAGE_PATH,
                        {
                            **SendTelegramMessageTest.MESSAGE_BODY_TEMPLATE_WITH_PREVIEW,
                            "link_preview_options": '{"is_disabled": false}',
                            "text": text,
                        },
                    ),
                    SendTelegramMessageTest.RESPONSE,
                )
            ]
        )

        send_telegram_message(self.test_chat, text, disable_preview=False)

    def test_send_telegram_message_reply_to_message_id(self):
        """Test that additional kwargs are sent in the request"""
        text = "Hello"

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        SendTelegramMessageTest.SEND_MESSAGE_PATH,
                        {
                            **SendTelegramMessageTest.MESSAGE_BODY_TEMPLATE,
                            "text": text,
                            "reply_parameters": '{"message_id": 999}',
                        },
                    ),
                    SendTelegramMessageTest.RESPONSE,
                )
            ]
        )

        send_telegram_message(self.test_chat, text, reply_to_message_id=999)

    def test_send_telegram_message_reply_markup(self):
        """Test that reply_markup is sent in the request"""
        text = "Hello with buttons"
        # Create a simple inline keyboard
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="Click me", callback_data="test")]]
        )

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        SendTelegramMessageTest.SEND_MESSAGE_PATH,
                        {
                            **SendTelegramMessageTest.MESSAGE_BODY_TEMPLATE,
                            "text": text,
                            "reply_markup": '{"inline_keyboard": [[{"callback_data": "test", "text": "Click me"}]]}',
                        },
                    ),
                    SendTelegramMessageTest.RESPONSE,
                )
            ]
        )

        send_telegram_message(self.test_chat, text, reply_markup=keyboard)

    def test_send_telegram_image(self):
        """Test sending an image directly"""
        image_url = "https://example.com/test_image.jpg"
        caption = "Test image caption"

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        SendTelegramMessageTest.SEND_PHOTO_PATH,
                        {
                            **SendTelegramMessageTest.MESSAGE_BODY_TEMPLATE_WITH_PREVIEW,
                            "photo": image_url,
                            "caption": caption,
                        },
                    ),
                    SendTelegramMessageTest.RESPONSE,
                )
            ]
        )

        send_telegram_image(self.test_chat, image_url, caption)

    def test_send_telegram_image_truncation(self):
        """Test that image captions are truncated to PHOTO_TEXT_LIMIT"""
        image_url = "https://example.com/test_image.jpg"
        long_caption = "A" * 2000
        truncated_caption = "A" * 1024

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        SendTelegramMessageTest.SEND_PHOTO_PATH,
                        {
                            **SendTelegramMessageTest.MESSAGE_BODY_TEMPLATE_WITH_PREVIEW,
                            "photo": image_url,
                            "caption": truncated_caption,
                        },
                    ),
                    SendTelegramMessageTest.RESPONSE,
                )
            ]
        )

        send_telegram_image(self.test_chat, image_url, long_caption)

    def test_send_telegram_image_parse_mode(self):
        """Test that parse_mode is sent with image"""
        image_url = "https://example.com/test_image.jpg"
        caption = "Image with markdown"

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        SendTelegramMessageTest.SEND_PHOTO_PATH,
                        {
                            **SendTelegramMessageTest.MESSAGE_BODY_TEMPLATE_WITH_PREVIEW,
                            "photo": image_url,
                            "caption": caption,
                            "parse_mode": "Markdown",
                        },
                    ),
                    SendTelegramMessageTest.RESPONSE,
                )
            ]
        )

        send_telegram_image(
            self.test_chat, image_url, caption, parse_mode="Markdown"
        )

    def test_send_telegram_message_returns_message_object(self):
        text = "Return value test"

        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        SendTelegramMessageTest.SEND_MESSAGE_PATH,
                        {
                            **SendTelegramMessageTest.MESSAGE_BODY_TEMPLATE,
                            "text": text,
                        },
                    ),
                    SendTelegramMessageTest.RESPONSE,
                )
            ]
        )

        result = send_telegram_message(self.test_chat, text)

        self.assertIsNotNone(result, "send_telegram_message returned None instead of Message")
        self.assertEqual(result.message_id, 123456)

    def test_send_telegram_message_consecutive_calls(self):
        """Second call uses message_id from the first as reply_to."""
        self.server.expect_requests(
            [
                ExpectedRequest(
                    Request(
                        "POST",
                        SendTelegramMessageTest.SEND_MESSAGE_PATH,
                        {
                            **SendTelegramMessageTest.MESSAGE_BODY_TEMPLATE,
                            "text": "First message",
                        },
                    ),
                    SendTelegramMessageTest.RESPONSE,
                ),
                ExpectedRequest(
                    Request(
                        "POST",
                        SendTelegramMessageTest.SEND_MESSAGE_PATH,
                        {
                            **SendTelegramMessageTest.MESSAGE_BODY_TEMPLATE,
                            "text": "Reply to first",
                            "reply_parameters": '{"message_id": 123456}',
                        },
                    ),
                    SendTelegramMessageTest.RESPONSE,
                ),
            ]
        )

        first = send_telegram_message(self.test_chat, "First message")
        self.assertIsNotNone(first)

        second = send_telegram_message(
            self.test_chat, "Reply to first",
            reply_to_message_id=first.message_id,
        )
        self.assertIsNotNone(second)
