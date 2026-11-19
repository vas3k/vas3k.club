from unittest.mock import MagicMock

from django.test import SimpleTestCase, override_settings
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


class TestReplyRouting(SimpleTestCase):
    @override_settings(TELEGRAM_TOKEN="123:ABC", TELEGRAM_ADMIN_CHAT_ID="-100999")
    def test_conversation_replies_and_existing_actions(self):
        from bot.main import build_application
        from bot.handlers import llm, comments, upvotes, whois

        application = build_application()
        bot = MagicMock(spec=Bot)
        bot.id = 123
        bot.username = "club_bot"

        for original, text, sender, chat_id, caption, edited, expected in (
            ("AI answer", "Tell me more", 123, -100111, False, False, llm.llm_response),
            ("AI answer", "Tell me more", 123, 42, False, False, llm.llm_response),
            ("AI answer", "Tell me more", 123, -100999, False, False, llm.llm_response),
            ("AI answer", "Explain this", 123, -100111, True, False, llm.llm_response),
            ("AI answer", "Edited", 123, -100111, False, True, None),
            ("Someone else", "Tell me more", 456, -100111, False, False, None),
            ("📝 Club post", "My comment", 123, -100111, False, False, comments.comment),
            ("💬 Club comment", "My reply", 123, -100111, False, False, comments.comment),
            ("📝 Club post", "+", 123, -100111, False, False, upvotes.upvote),
            ("AI answer", "/whois", 123, -100111, False, False, whois.command_whois),
        ):
            with self.subTest(original=original, text=text, chat_id=chat_id, caption=caption, edited=edited):
                data = {
                    "message_id": 10, "date": 1,
                    "chat": {"id": chat_id, "type": "private" if chat_id > 0 else "supergroup"},
                    "caption" if caption else "text": text,
                    "reply_to_message": {
                        "message_id": 9, "date": 1,
                        "chat": {"id": chat_id, "type": "supergroup"}, "text": original,
                        "from": {"id": sender, "is_bot": True, "first_name": "Bot"},
                    },
                }

                if text.startswith("/"):
                    data["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text)}]

                message = Message.de_json(data, bot)
                update = Update(1, **{"edited_message" if edited else "message": message})
                callback = next((handler.callback for handler in application.handlers[0]
                                 if handler.check_update(update)), None)
                self.assertIs(callback, expected)
