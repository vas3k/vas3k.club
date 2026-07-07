from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from rooms.helpers import ban_user_in_all_chats
from rooms.models import Room
from users.models.user import User


def _create_user(slug, telegram_id=None):
    return User.objects.create(
        slug=slug,
        email=f"{slug}@test.com",
        full_name=slug,
        telegram_id=telegram_id,
        membership_started_at=datetime.utcnow() - timedelta(days=10),
        membership_expires_at=datetime.utcnow() + timedelta(days=10),
        moderation_status=User.MODERATION_STATUS_APPROVED,
        is_email_verified=True,
    )


class TestRoomsHelpers(TestCase):
    @patch("rooms.helpers.bot")
    def test_ban_user_skips_users_without_telegram(self, mock_bot):
        user = _create_user("room_no_tg")

        ban_user_in_all_chats(user=user)

        mock_bot.get_chat_member.assert_not_called()
        mock_bot.ban_chat_member.assert_not_called()

    @patch("rooms.helpers.bot")
    def test_ban_user_kicks_user_for_non_permanent(self, mock_bot):
        user = _create_user("room_tg_user", telegram_id="123")
        Room.objects.create(
            slug="room-chat-1",
            title="Room Chat",
            color="#222222",
            chat_id="999",
        )

        mock_bot.get_chat_member.return_value = SimpleNamespace(status="member")
        mock_bot.ban_chat_member.return_value = True

        ban_user_in_all_chats(user=user, is_permanent=False)

        mock_bot.get_chat_member.assert_called_once_with("999", "123")
        mock_bot.ban_chat_member.assert_called_once_with("999", "123")
        mock_bot.unban_chat_member.assert_called_once_with("999", "123")
