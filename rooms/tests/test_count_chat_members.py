from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from rooms.models import Room
from users.models.user import User


class TestCountChatMembers(TestCase):
    def setUp(self):
        self.room = Room.objects.create(
            slug="test-room",
            title="Test Room",
            color="#000000",
            chat_id="-100123",
        )
        self.admin_user = User.objects.create(
            email="room_admin@xx.com",
            slug="room_admin",
            telegram_id="111",
            moderation_status=User.MODERATION_STATUS_APPROVED,
        )
        self.other_admin_user = User.objects.create(
            email="other_admin@xx.com",
            slug="other_admin",
            telegram_id="222",
            moderation_status=User.MODERATION_STATUS_APPROVED,
        )

    def _make_chat_admin(self, telegram_id, is_bot=False):
        chat_admin = MagicMock()
        chat_admin.user.id = int(telegram_id)
        chat_admin.user.is_bot = is_bot
        return chat_admin

    @patch("rooms.management.commands.count_chat_members.bot")
    def test_syncs_admins_from_telegram(self, mock_bot):
        mock_bot.get_chat_member_count.return_value = 42
        mock_bot.get_chat_administrators.return_value = [
            self._make_chat_admin("111"),
            self._make_chat_admin("222"),
        ]

        call_command("count_chat_members", stdout=StringIO())

        self.room.refresh_from_db()
        self.assertEqual(self.room.chat_member_count, 42)
        self.assertEqual(self.room.admins, ["other_admin", "room_admin"])

    @patch("rooms.management.commands.count_chat_members.bot")
    def test_ignores_unknown_and_bot_admins(self, mock_bot):
        self.room.admins = ["old_admin"]
        self.room.save()

        mock_bot.get_chat_member_count.return_value = 10
        mock_bot.get_chat_administrators.return_value = [
            self._make_chat_admin("111"),
            self._make_chat_admin("999"),
            self._make_chat_admin("333", is_bot=True),
        ]

        call_command("count_chat_members", stdout=StringIO())

        self.room.refresh_from_db()
        self.assertEqual(self.room.admins, ["room_admin"])

    @patch("rooms.management.commands.count_chat_members.bot")
    def test_skips_room_on_telegram_error(self, mock_bot):
        from telegram.error import TelegramError

        mock_bot.get_chat_member_count.side_effect = TelegramError("chat not found")
        mock_bot.get_chat_administrators.side_effect = TelegramError("chat not found")

        call_command("count_chat_members", stdout=StringIO())

        self.room.refresh_from_db()
        self.assertEqual(self.room.chat_member_count, 0)
        self.assertEqual(self.room.admins, [])

    @patch("rooms.management.commands.count_chat_members.bot")
    def test_updates_member_count_when_admin_sync_fails(self, mock_bot):
        from telegram.error import TelegramError

        mock_bot.get_chat_member_count.return_value = 99
        mock_bot.get_chat_administrators.side_effect = TelegramError("no rights")

        call_command("count_chat_members", stdout=StringIO())

        self.room.refresh_from_db()
        self.assertEqual(self.room.chat_member_count, 99)
        self.assertEqual(self.room.admins, [])
