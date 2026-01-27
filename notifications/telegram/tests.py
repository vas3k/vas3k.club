from dataclasses import dataclass
import json
import http.server
import logging
import socketserver
import threading
import time
from typing import Any, Protocol
from unittest.mock import patch

import django
from django.test import TestCase
import telegram

from notifications.telegram.common import (
    send_telegram_message,
    send_telegram_image,
    Chat,
)
import difflib

django.setup()

log = logging.getLogger(__name__)


@dataclass
class Request:
    method: str
    path: str
    body: dict[str, str]


@dataclass
class ExpectedRequest:
    request: Request
    response: str
    wait: float = 0


class MockTelegramHandler(http.server.BaseHTTPRequestHandler):
    """Mock HTTP handler to capture Telegram API requests"""

    remaining_expected_requests: list[ExpectedRequest] = []
    test_case: TestCase

    def _do_handle(self, request):
        expected_request = self._get_server().pop_expected_request()

        if request != expected_request.request:
            self.send_response(400)
            self.end_headers()
            self.wfile.write("Request doesn't match expected".encode())

            request_json = json.dumps(request.__dict__, indent=2, sort_keys=True)
            expected_json = json.dumps(
                expected_request.request.__dict__, indent=2, sort_keys=True
            )
            diff = "\n".join(
                difflib.unified_diff(
                    expected_json.splitlines(),
                    request_json.splitlines(),
                    fromfile="expected",
                    tofile="actual",
                    lineterm="",
                )
            )
            log.error(f"Request mismatch diff:\n{diff}")

            self._get_server().report_request_unsuccessful()
            self._get_server().test_case.fail("Request mismatch")

        if expected_request.wait > 0:
            time.sleep(expected_request.wait)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(expected_request.response.encode())

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        body_str = body.decode("utf-8") if body else ""

        request = Request(
            path=self.path,
            method=self.command,
            body=json.loads(body_str),
        )

        self._do_handle(request)

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
    bot: telegram.Bot
    patcher: Any

    def setUp(self) -> None: ...
    def tearDown(self) -> None: ...
    def assertTrue(self, expr, msg=None): ...
    def fail(self, msg=None): ...


class MockTelegramServer(socketserver.TCPServer):
    test_case: TelegramTestCaseProtocol
    remaining_expected_requests: list[ExpectedRequest] | None = None
    all_requests_successful = True

    def __init__(self, test_case: TelegramTestCaseProtocol, *args, **kwargs) -> None:
        self.test_case = test_case
        super().__init__(*args, **kwargs)

    def expect_requests(self, expected_requests: list[ExpectedRequest]):
        if self.remaining_expected_requests is not None:
            raise RuntimeError("expect_requests can only be called once")

        self.remaining_expected_requests = expected_requests

    def pop_expected_request(self):
        if self.remaining_expected_requests is None:
            raise RuntimeError("expect_requests not called")

        return self.remaining_expected_requests.pop(0)

    def report_request_unsuccessful(self):
        self.all_requests_successful = False

    def check_requests(self):
        self.test_case.assertTrue(
            self.all_requests_successful, "some requests were unsuccessful"
        )
        self.test_case.assertTrue(
            self.remaining_expected_requests is None
            or len(self.remaining_expected_requests) == 0,
            f"some requests not executed: {self.remaining_expected_requests}",
        )


class BaseTelegramTest:
    tags = ["telegram"]

    TOKEN = "123456789:ABCDefGhijklmnOpqrstuvWxyzAbcdefghijk"
    SEND_MESSAGE_PATH = f"/{TOKEN}/sendMessage"
    SEND_PHOTO_PATH = f"/{TOKEN}/sendPhoto"

    def setUp(self: TelegramTestCaseProtocol):
        self.server = MockTelegramServer(
            test_case=self,
            server_address=("127.0.0.1", 0),
            RequestHandlerClass=MockTelegramHandler,
        )

        server_port = self.server.server_address[1]
        server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        server_thread.daemon = True
        server_thread.start()

        # Create a real bot that points to our test server
        # Use a valid token format to pass validation
        self.bot = telegram.Bot(
            base_url=f"http://127.0.0.1:{server_port}/",
            token=SendTelegramMessageTest.TOKEN,
        )
        self.patcher = patch("notifications.telegram.common.bot", self.bot)
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
        "disable_web_page_preview": "True",
        "disable_notification": "False",
    }

    MESSAGE_BODY_TEMPLATE_WITH_PREVIEW = {
        k: v
        for k, v in MESSAGE_BODY_TEMPLATE.items()
        if k != "disable_web_page_preview"
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
                            "parse_mode": telegram.ParseMode.MARKDOWN,
                        },
                    ),
                    SendTelegramMessageTest.RESPONSE,
                )
            ]
        )

        send_telegram_message(
            self.test_chat, text, parse_mode=telegram.ParseMode.MARKDOWN
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
                            "reply_to_message_id": "999",
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
        keyboard = telegram.InlineKeyboardMarkup(
            [[telegram.InlineKeyboardButton(text="Click me", callback_data="test")]]
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
                            "reply_markup": '{"inline_keyboard": [[{"text": "Click me", "callback_data": "test"}]]}',
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
                            "parse_mode": telegram.ParseMode.MARKDOWN,
                        },
                    ),
                    SendTelegramMessageTest.RESPONSE,
                )
            ]
        )

        send_telegram_image(
            self.test_chat, image_url, caption, parse_mode=telegram.ParseMode.MARKDOWN
        )
