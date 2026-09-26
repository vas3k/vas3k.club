import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import SimpleTestCase

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

    def test_topic_reply_still_looks_up_replied_author(self):
        # Forum topics set reply_to_message to the topic root. That must stay a person lookup.
        replied = _replied_author(77, message_id=555)
        update = _update(_message(
            text="/whois @someone",
            reply_to_message=replied,
            message_thread_id=555,
        ))

        user_filter = self._run(update, found_user=_club_user(slug="carol", full_name="Carol"))

        user_filter.assert_called_once_with(telegram_id=77)
        text = update.message.reply_text.await_args.args[0]
        self.assertIn("Carol", text)

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
