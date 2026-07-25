from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from rooms.helpers import ban_user_in_all_chats, get_user_chats
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

        before = datetime.utcnow()
        ban_user_in_all_chats(user=user, is_permanent=False)
        after = datetime.utcnow()

        mock_bot.get_chat_member.assert_called_once_with("999", "123")
        mock_bot.ban_chat_member.assert_called_once()
        args, kwargs = mock_bot.ban_chat_member.call_args
        self.assertEqual(args[:2], ("999", "123"))
        self.assertGreaterEqual(kwargs["until_date"], before + timedelta(minutes=5))
        self.assertLessEqual(kwargs["until_date"], after + timedelta(minutes=5))
        mock_bot.unban_chat_member.assert_not_called()

    @patch("rooms.helpers.bot")
    def test_ban_user_permanent_has_no_until_date(self, mock_bot):
        user = _create_user("room_permanent", telegram_id="123")
        Room.objects.create(
            slug="room-chat-2",
            title="Room Chat 2",
            color="#222222",
            chat_id="888",
        )

        mock_bot.get_chat_member.return_value = SimpleNamespace(status="member")
        mock_bot.ban_chat_member.return_value = True

        ban_user_in_all_chats(user=user, is_permanent=True)

        mock_bot.ban_chat_member.assert_called_once_with("888", "123", until_date=None)
        mock_bot.unban_chat_member.assert_not_called()

    @patch("rooms.helpers.bot")
    def test_get_user_chats_returns_active_memberships(self, mock_bot):
        user = _create_user("room_list_user", telegram_id="123")
        Room.objects.create(slug="room-a", title="Room A", color="#111111", chat_id="1")
        Room.objects.create(slug="room-b", title="Room B", color="#222222", chat_id="2")
        Room.objects.create(slug="room-c", title="Room C", color="#333333", chat_id="3")

        def get_chat_member(chat_id, telegram_id):
            statuses = {
                "1": "member",
                "2": "left",
                "3": "administrator",
            }
            return SimpleNamespace(status=statuses[chat_id])

        mock_bot.get_chat_member.side_effect = get_chat_member

        chats = get_user_chats(user)

        self.assertEqual([room.title for room in chats], ["Room A", "Room C"])
