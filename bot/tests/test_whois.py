import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import SimpleTestCase
from telegram import Bot, Message, MessageOriginHiddenUser, MessageOriginUser, Update
from datetime import datetime

from bot.handlers.whois import command_whois


def _club_user(slug="bob", full_name="Bob"):
    return SimpleNamespace(slug=slug, full_name=full_name)


def _message(**overrides):
    message = dict(
        text="/whois",
        reply_to_message=None,
        forward_origin=None,
        chat=SimpleNamespace(type="supergroup"),
        from_user=SimpleNamespace(id=1, is_bot=False),
        reply_text=AsyncMock(),
        message_thread_id=None,
        is_topic_message=False,
    )
    message.update(overrides)
    return SimpleNamespace(**message)


def _update(message, user_id=1):
    return SimpleNamespace(
        message=message,
        effective_user=SimpleNamespace(id=user_id),
        callback_query=None,
    )


def _replied_author(telegram_id, message_id=10):
    return SimpleNamespace(
        id=message_id,
        from_user=SimpleNamespace(id=telegram_id, is_bot=False),
        forward_origin=None,
        sender_chat=None,
    )


class TestWhois(SimpleTestCase):
    def _run(self, update, found_user=None, club_user_ids=None):
        if club_user_ids is None:
            club_user_ids = [str(update.effective_user.id)]
        queryset = MagicMock()
        queryset.first.return_value = found_user
        user_filter = MagicMock(return_value=queryset)
        with patch("bot.decorators.cached_telegram_users", return_value=club_user_ids), \
                patch("bot.handlers.whois.User.objects.filter", user_filter):
            asyncio.run(command_whois(update, SimpleNamespace()))
        return user_filter

    def test_reply_looks_up_replied_author(self):
        update = _update(_message(reply_to_message=_replied_author(99)))

        user_filter = self._run(update, found_user=_club_user())

        user_filter.assert_called_once_with(telegram_id=99)
        text = update.message.reply_text.await_args.args[0]
        self.assertIn("Bob", text)
        self.assertIn("/user/bob/", text)

    def test_topic_root_does_not_override_explicit_username(self):
        replied = _replied_author(77, message_id=555)
        update = _update(_message(
            text="/whois @Bob",
            reply_to_message=replied,
            message_thread_id=555,
            is_topic_message=True,
        ))

        user_filter = self._run(update, found_user=_club_user())

        user_filter.assert_called_once_with(
            telegram_id__isnull=False, telegram_data__username__iexact="Bob",
        )
        self.assertIn("/user/bob/", update.message.reply_text.await_args.args[0])

    def test_real_reply_in_topic_looks_up_replied_author(self):
        update = _update(_message(
            reply_to_message=_replied_author(99, message_id=556),
            message_thread_id=555,
            is_topic_message=True,
        ))

        user_filter = self._run(update, found_user=_club_user())

        user_filter.assert_called_once_with(telegram_id=99)

    def test_empty_target_in_topic_never_looks_up_topic_creator(self):
        for text in ("/whois", "/whois ", "/whois @", "/whois@club_bot @", "/whois @@"):
            with self.subTest(text=text):
                update = _update(_message(
                    text=text, reply_to_message=_replied_author(77, message_id=555), message_thread_id=555,
                    is_topic_message=True,
                ))

                user_filter = self._run(update, found_user=_club_user(slug="vas3k"))

                user_filter.assert_not_called()
                self.assertNotIn("/user/vas3k/", update.message.reply_text.await_args.args[0])

    def test_numeric_target_in_topic_never_looks_up_topic_creator(self):
        update = _update(_message(
            text="/whois 99", reply_to_message=_replied_author(77, message_id=555), message_thread_id=555,
            is_topic_message=True,
        ))

        user_filter = self._run(update, found_user=_club_user())

        user_filter.assert_called_once_with(telegram_id="99")

    def test_unknown_target_in_topic_never_falls_back_to_topic_creator(self):
        update = _update(_message(
            text="/whois @missing", reply_to_message=_replied_author(77, message_id=555), message_thread_id=555,
            is_topic_message=True,
        ))

        user_filter = self._run(update)

        user_filter.assert_called_once_with(
            telegram_id__isnull=False, telegram_data__username__iexact="missing",
        )
        self.assertIn("не найден", update.message.reply_text.await_args.args[0])

    def test_private_forward_looks_up_original_sender_without_arguments(self):
        sender = SimpleNamespace(id=99, is_bot=False)
        update = _update(_message(
            text="Forwarded text", chat=SimpleNamespace(type="private"),
            forward_origin=MessageOriginUser(date=datetime(2026, 1, 1), sender_user=sender),
        ))

        user_filter = self._run(update, found_user=_club_user())

        user_filter.assert_called_once_with(telegram_id=99)

    def test_private_forward_with_hidden_sender_does_not_look_up_forwarder(self):
        update = _update(_message(
            text="Forwarded text", chat=SimpleNamespace(type="private"),
            forward_origin=MessageOriginHiddenUser(date=datetime(2026, 1, 1), sender_user_name="Hidden"),
        ))

        user_filter = self._run(update, found_user=_club_user(slug="vas3k"))

        user_filter.assert_not_called()

    def test_username_without_reply(self):
        update = _update(_message(text="/whois @Bob"))

        user_filter = self._run(update, found_user=_club_user())

        user_filter.assert_called_once_with(
            telegram_id__isnull=False,
            telegram_data__username__iexact="Bob",
        )
        text = update.message.reply_text.await_args.args[0]
        self.assertIn("/user/bob/", text)

    def test_bare_whois_without_reply_asks_for_usage(self):
        update = _update(_message(text="/whois"))

        user_filter = self._run(update)

        user_filter.assert_not_called()
        text = update.message.reply_text.await_args.args[0]
        self.assertIn("/whois @username", text)

    def test_unknown_username(self):
        update = _update(_message(text="/whois @missing"))

        self._run(update, found_user=None)

        text = update.message.reply_text.await_args.args[0]
        self.assertIn("не найден", text)

    def test_outsider_is_asked_to_link_the_bot(self):
        update = _update(_message(text="/whois @Bob"))

        user_filter = self._run(update, club_user_ids=[])

        user_filter.assert_not_called()
        text = update.message.reply_text.await_args.args[0]
        self.assertIn("Привяжи", text)

    def test_reply_chain_root_is_a_person_not_a_forum_topic(self):
        update = _update(_message(
            reply_to_message=_replied_author(99, message_id=555), message_thread_id=555,
        ))

        user_filter = self._run(update, found_user=_club_user())

        user_filter.assert_called_once_with(telegram_id=99)

    def test_reply_to_forwarded_message_looks_up_chat_participant(self):
        replied = _replied_author(99)
        replied.forward_origin = MessageOriginUser(
            date=datetime(2026, 1, 1), sender_user=SimpleNamespace(id=77, is_bot=False),
        )
        update = _update(_message(reply_to_message=replied))

        user_filter = self._run(update, found_user=_club_user())

        user_filter.assert_called_once_with(telegram_id=99)

    def test_private_channel_forward_never_looks_up_forwarder(self):
        for origin_type in ("channel", "chat"):
            with self.subTest(origin_type=origin_type):
                update = _update(_message(
                    chat=SimpleNamespace(type="private"),
                    forward_origin=SimpleNamespace(type=origin_type),
                ))

                user_filter = self._run(update)

                user_filter.assert_not_called()

    def test_reply_without_person_never_queries_empty_id(self):
        for sender in (None, SimpleNamespace(id=77, is_bot=False), SimpleNamespace(id=77, is_bot=True)):
            with self.subTest(sender=sender):
                replied = _replied_author(99)
                replied.from_user = sender
                replied.sender_chat = SimpleNamespace(id=-100123)
                update = _update(_message(reply_to_message=replied))

                user_filter = self._run(update)

                user_filter.assert_not_called()

    def test_numeric_target_in_private_chat(self):
        update = _update(_message(text="/whois 99", chat=SimpleNamespace(type="private")))

        user_filter = self._run(update, found_user=_club_user())

        user_filter.assert_called_once_with(telegram_id="99")

    def test_reply_is_sent_to_original_chat_and_topic(self):
        for is_topic in (False, True):
            with self.subTest(is_topic=is_topic):
                bot = Bot("123456:TEST")
                message = Message.de_json({
                    "message_id": 600,
                    "date": 1,
                    "chat": {"id": -100123, "type": "supergroup"},
                    "from": {"id": 1, "is_bot": False, "first_name": "Caller"},
                    "text": "/whois",
                    "is_topic_message": is_topic,
                    "message_thread_id": 555,
                    "reply_to_message": {
                        "message_id": 556 if is_topic else 555,
                        "date": 1,
                        "chat": {"id": -100123, "type": "supergroup"},
                        "from": {"id": 99, "is_bot": False, "first_name": "Target"},
                    },
                }, bot)
                update = Update(update_id=1, message=message)

                with patch.object(Bot, "send_message", new_callable=AsyncMock) as send:
                    user_filter = self._run(update, found_user=_club_user())

                user_filter.assert_called_once_with(telegram_id=99)
                send.assert_awaited_once()
                self.assertEqual(send.await_args.kwargs["chat_id"], -100123)
                self.assertEqual(send.await_args.kwargs["reply_parameters"].message_id, 600)
                self.assertEqual(send.await_args.kwargs["message_thread_id"], 555 if is_topic else None)
