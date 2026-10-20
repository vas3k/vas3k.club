from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings
from telethon.errors import FloodWaitError


@override_settings(TELEGRAM_API_ID="123", TELEGRAM_API_HASH="test", TELEGRAM_TOKEN="test")
class TestRemoveExpiredUsersFromChat(SimpleTestCase):
    def test_entity_lookup_recovers_after_delay(self):
        with patch("rooms.management.commands.remove_expired_users_from_chat.TelegramClient") as client, \
                patch("rooms.management.commands.remove_expired_users_from_chat.time.sleep") as sleep:
            client.return_value.get_entity.side_effect = [ValueError("Missing input entity"), "chat"]
            client.return_value.get_participants.return_value = []
            call_command("remove_expired_users_from_chat", chat_id="-100123", stdout=StringIO())

        self.assertEqual(client.return_value.get_entity.call_count, 2)
        sleep.assert_called_once_with(60)
        client.return_value.edit_permissions.assert_not_called()

    def test_participant_fetch_recovers_after_connection_failure(self):
        with patch("rooms.management.commands.remove_expired_users_from_chat.TelegramClient") as client, \
                patch("rooms.management.commands.remove_expired_users_from_chat.time.sleep") as sleep:
            client.return_value.get_participants.side_effect = [OSError("Disconnected"), [], []]
            call_command("remove_expired_users_from_chat", chat_id="-100123", stdout=StringIO())

        self.assertEqual(client.return_value.get_participants.call_count, 3)
        sleep.assert_called_once_with(60)

    def test_admin_fetch_failure_aborts_without_removing_anyone(self):
        with patch("rooms.management.commands.remove_expired_users_from_chat.TelegramClient") as client, \
                patch("rooms.management.commands.remove_expired_users_from_chat.time.sleep") as sleep:
            client.return_value.get_participants.side_effect = [
                [SimpleNamespace(id=123)],
                OSError("Admin list unavailable"), OSError("Admin list unavailable"), OSError("Admin list unavailable"),
            ]

            with self.assertRaisesMessage(CommandError, "no users removed"):
                call_command("remove_expired_users_from_chat", chat_id="-100123", execute=True, stdout=StringIO())

        client.return_value.edit_permissions.assert_not_called()
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [60, 120])

    def test_removal_resumes_after_flood_wait_and_stays_temporary(self):
        with patch("rooms.management.commands.remove_expired_users_from_chat.TelegramClient") as client, \
                patch("rooms.management.commands.remove_expired_users_from_chat.User.objects.filter") as users, \
                patch("rooms.management.commands.remove_expired_users_from_chat.time.sleep") as sleep:
            users.return_value.first.return_value = None
            client.return_value.get_participants.side_effect = [[SimpleNamespace(id=123)], []]
            client.return_value.edit_permissions.side_effect = [FloodWaitError(request=None, capture=300), None]
            call_command("remove_expired_users_from_chat", chat_id="-100123", execute=True, stdout=StringIO())

        self.assertEqual(client.return_value.edit_permissions.call_count, 2)
        self.assertEqual(sleep.call_args_list[0].args, (301,))

        for call in client.return_value.edit_permissions.call_args_list:
            self.assertEqual(call.kwargs["until_date"], timedelta(minutes=5))
            self.assertFalse(call.kwargs["view_messages"])

    def test_chat_admins_are_never_removed(self):
        with patch("rooms.management.commands.remove_expired_users_from_chat.TelegramClient") as client, \
                patch("rooms.management.commands.remove_expired_users_from_chat.User.objects.filter") as users:
            users.return_value.first.return_value = None
            participant = SimpleNamespace(id=123)
            client.return_value.get_participants.side_effect = [[participant], [participant]]
            call_command("remove_expired_users_from_chat", chat_id="-100123", execute=True, stdout=StringIO())

        client.return_value.edit_permissions.assert_not_called()

    def test_persistent_entity_failure_reports_error_without_removing_users(self):
        with patch("rooms.management.commands.remove_expired_users_from_chat.TelegramClient") as client, \
                patch("rooms.management.commands.remove_expired_users_from_chat.time.sleep") as sleep:
            client.return_value.get_entity.side_effect = ValueError("Missing input entity")

            with self.assertRaises(CommandError):
                call_command("remove_expired_users_from_chat", chat_id="-100123", execute=True, stdout=StringIO())

        self.assertEqual(client.return_value.get_entity.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [60, 120])
        client.return_value.edit_permissions.assert_not_called()

    def test_dry_run_does_not_remove_expired_or_unknown_users(self):
        with patch("rooms.management.commands.remove_expired_users_from_chat.TelegramClient") as client, \
                patch("rooms.management.commands.remove_expired_users_from_chat.User.objects.filter") as users:
            users.return_value.first.return_value = None
            client.return_value.get_participants.side_effect = [[SimpleNamespace(id=123)], []]
            call_command("remove_expired_users_from_chat", chat_id="-100123", stdout=StringIO())

        client.return_value.edit_permissions.assert_not_called()
