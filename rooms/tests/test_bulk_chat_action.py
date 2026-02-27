from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from users.models.user import User


class TestBulkChatAction(TestCase):
    def setUp(self):
        self.users = []
        for i in range(5):
            user = User.objects.create(
                email=f"bulk_user_{i}@xx.com",
                membership_started_at=datetime.now() - timedelta(days=5),
                membership_expires_at=datetime.now() + timedelta(days=5),
                moderation_status=User.MODERATION_STATUS_APPROVED,
                slug=f"bulk_user_{i}",
            )
            self.users.append(user)

    @patch("rooms.management.commands.bulk_chat_action.ban_user_in_all_chats")
    def test_bans_users_by_slug(self, mock_ban):
        slugs = ",".join(u.slug for u in self.users)

        with self.assertNumQueries(1):
            call_command("bulk_chat_action", "--users", slugs, "--action", "ban", stdout=StringIO())

        self.assertEqual(mock_ban.call_count, 5)
        for user in self.users:
            mock_ban.assert_any_call(user, is_permanent=True)

    @patch("rooms.management.commands.bulk_chat_action.ban_user_in_all_chats")
    def test_bans_users_by_email(self, mock_ban):
        emails = ",".join(u.email for u in self.users)

        with self.assertNumQueries(1):
            call_command("bulk_chat_action", "--users", emails, "--action", "ban", stdout=StringIO())

        self.assertEqual(mock_ban.call_count, 5)

    @patch("rooms.management.commands.bulk_chat_action.unban_user_in_all_chats")
    def test_unbans_users(self, mock_unban):
        slugs = ",".join(u.slug for u in self.users)

        call_command("bulk_chat_action", "--users", slugs, "--action", "unban", stdout=StringIO())

        self.assertEqual(mock_unban.call_count, 5)

    @patch("rooms.management.commands.bulk_chat_action.ban_user_in_all_chats")
    def test_skips_missing_users(self, mock_ban):
        stderr = StringIO()
        call_command(
            "bulk_chat_action",
            "--users", "nonexistent_slug",
            "--action", "ban",
            stdout=StringIO(),
            stderr=stderr,
        )

        mock_ban.assert_not_called()
        self.assertIn("No such user", stderr.getvalue())

    @patch("rooms.management.commands.bulk_chat_action.ban_user_in_all_chats")
    def test_mixed_email_and_slug_lookup(self, mock_ban):
        identifiers = f"{self.users[0].email},{self.users[1].slug}"

        call_command("bulk_chat_action", "--users", identifiers, "--action", "ban", stdout=StringIO())

        self.assertEqual(mock_ban.call_count, 2)

    @patch("rooms.management.commands.bulk_chat_action.ban_user_in_all_chats")
    @patch("rooms.management.commands.bulk_chat_action.unban_user_in_all_chats")
    def test_wrong_action_writes_error(self, mock_unban, mock_ban):
        stderr = StringIO()
        call_command(
            "bulk_chat_action",
            "--users", self.users[0].slug,
            "--action", "invalid",
            stdout=StringIO(),
            stderr=stderr,
        )

        mock_ban.assert_not_called()
        mock_unban.assert_not_called()
        self.assertIn("Wrong action", stderr.getvalue())
