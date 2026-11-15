from unittest.mock import MagicMock

from django.test import SimpleTestCase
from telegram import Bot, Message, Update

from bot.filters import ReplyToBot
from telegram.ext import filters


class TestReplyToBot(SimpleTestCase):
    def test_only_new_replies_to_this_bot_match(self):
        bot = MagicMock(spec=Bot)
        bot.id = 123
        comment_filter = filters.UpdateType.MESSAGE & ReplyToBot() & ~filters.Chat(-100999)

        for sender_id, chat_id, edited, expected in (
            (123, -100111, False, True),
            (123, 42, False, True),
            (456, -100111, False, False),
            (None, -100111, False, False),
            (123, -100999, False, False),
            (123, -100111, True, False),
        ):
            with self.subTest(sender_id=sender_id, chat_id=chat_id, edited=edited):
                message = Message.de_json({
                    "message_id": 10,
                    "date": 1,
                    "chat": {"id": chat_id, "type": "private" if chat_id > 0 else "supergroup"},
                    "reply_to_message": {
                        "message_id": 9,
                        "date": 1,
                        "chat": {"id": chat_id, "type": "supergroup"},
                        "from": {"id": sender_id, "is_bot": True, "first_name": "Bot"} if sender_id else None,
                    },
                }, bot)
                update = Update(1, **{"edited_message" if edited else "message": message})

                self.assertEqual(bool(comment_filter.check_update(update)), expected)

        message = Message.de_json({
            "message_id": 10,
            "date": 1,
            "chat": {"id": -100111, "type": "supergroup"},
            "text": "Not a reply",
        }, bot)
        self.assertFalse(comment_filter.check_update(Update(1, message=message)))
