from datetime import datetime, timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management import call_command, CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from debug.utils_for_tests import create_approved_user, login
from rooms.models import Room, RoomSubscription


class TestRoomMembership(TestCase):
    def setUp(self):
        self.user = create_approved_user("chat-member")
        self.user.telegram_id = "123"
        self.user.save()
        self.room = Room.objects.create(slug="chat-room", title="Chat room", color="#333", chat_id="-100123")

    def test_join_is_silent_and_idempotent(self):
        membership, created = RoomSubscription.join_chat(self.user, self.room)
        self.assertTrue(created)
        self.assertTrue(membership.is_chat_member)
        self.assertFalse(membership.is_notified)
        created_at = membership.created_at
        membership, created = RoomSubscription.join_chat(self.user, self.room)
        self.assertFalse(created)
        self.assertEqual(membership.created_at, created_at)
        self.assertFalse(RoomSubscription.is_subscribed(self.user, self.room))
        self.assertFalse(RoomSubscription.room_subscribers(self.room).exists())

    def test_join_preserves_notifications_and_leave_preserves_subscription(self):
        membership, created = RoomSubscription.subscribe(self.user, self.room)
        RoomSubscription.join_chat(self.user, self.room)
        RoomSubscription.leave_chat(self.user, self.room)
        membership.refresh_from_db()
        self.assertTrue(membership.is_notified)
        self.assertFalse(membership.is_chat_member)

    def test_unsubscribe_preserves_chat_membership(self):
        RoomSubscription.join_chat(self.user, self.room)
        RoomSubscription.subscribe(self.user, self.room)
        RoomSubscription.unsubscribe(self.user, self.room)
        membership = RoomSubscription.get(self.user, self.room)
        self.assertTrue(membership.is_chat_member)
        self.assertFalse(membership.is_notified)
        RoomSubscription.leave_chat(self.user, self.room)
        membership.refresh_from_db()
        self.assertFalse(membership.is_chat_member)
        self.assertFalse(membership.is_notified)

    def test_toggle_notifications_for_existing_member(self):
        RoomSubscription.join_chat(self.user, self.room)
        login(self.client, self.user)

        for method, expected in [(self.client.post, True), (self.client.delete, False)]:
            response = method(reverse("toggle_room_subscription", args=[self.room.slug]))
            self.assertEqual(response.status_code, 200)
            membership = RoomSubscription.get(self.user, self.room)
            self.assertEqual(membership.is_notified, expected)
            self.assertTrue(membership.is_chat_member)

    def test_duplicate_membership_rejected(self):
        RoomSubscription.join_chat(self.user, self.room)

        with self.assertRaises(IntegrityError), transaction.atomic():
            RoomSubscription.objects.create(user=self.user, room=self.room)


@override_settings(TELEGRAM_API_ID="123", TELEGRAM_API_HASH="test", TELEGRAM_TOKEN="test")
class TestRecalculateChatMembers(TestCase):
    def setUp(self):
        self.user = create_approved_user("sync-member")
        self.user.telegram_id = "123"
        self.user.save()
        self.room = Room.objects.create(slug="sync-room", title="Sync room", color="#333", chat_id="-100123")

    def test_sync_matches_ids_preserves_preferences_and_removes_departed_members(self):
        departed = create_approved_user("departed-member")
        subscribed = create_approved_user("subscribed-member")
        RoomSubscription.join_chat(departed, self.room)
        RoomSubscription.join_chat(subscribed, self.room)
        RoomSubscription.subscribe(subscribed, self.room)
        RoomSubscription.objects.update(created_at=datetime.utcnow() - timedelta(days=1))
        participants = MagicMock()
        participants.__iter__.return_value = iter([
            SimpleNamespace(id=123, bot=False), SimpleNamespace(id=456, bot=False),
            SimpleNamespace(id=789, bot=True),
        ])
        participants.__len__.return_value = 3
        participants.total = 3

        with patch("rooms.management.commands.recalculate_chat_members.TelegramClient") as client:
            client.return_value.get_participants.return_value = participants
            call_command("recalculate_chat_members", stdout=StringIO())

        membership = RoomSubscription.get(self.user, self.room)
        self.assertTrue(membership.is_chat_member)
        self.assertFalse(membership.is_notified)
        self.assertFalse(RoomSubscription.get(departed, self.room).is_chat_member)
        self.assertFalse(RoomSubscription.get(departed, self.room).is_notified)
        self.assertTrue(RoomSubscription.is_subscribed(subscribed, self.room))
        self.assertFalse(RoomSubscription.get(subscribed, self.room).is_chat_member)

    def test_sync_preserves_notification_preferences_on_join_leave_and_rejoin(self):
        for is_notified in [True, False]:
            subscription, created = RoomSubscription.objects.update_or_create(
                user=self.user, room=self.room, defaults={"is_notified": is_notified},
            )
            created_at = subscription.created_at

            for is_chat_member in [True, False, True]:
                participants = MagicMock()
                participants.__iter__.return_value = iter(
                    [SimpleNamespace(id=123, bot=False)] if is_chat_member else [],
                )
                participants.__len__.return_value = int(is_chat_member)
                participants.total = int(is_chat_member)

                with patch("rooms.management.commands.recalculate_chat_members.TelegramClient") as client:
                    client.return_value.get_participants.return_value = participants
                    call_command("recalculate_chat_members", stdout=StringIO())

                subscription.refresh_from_db()
                self.assertEqual(subscription.is_chat_member, is_chat_member)
                self.assertEqual(subscription.is_notified, is_notified)
                self.assertEqual(subscription.created_at, created_at)

    def test_sync_preserves_webhook_join_or_leave_received_during_fetch(self):
        for is_notified in [True, False]:
            for is_chat_member in [True, False]:
                with self.subTest(is_notified=is_notified, is_chat_member=is_chat_member):
                    RoomSubscription.objects.filter(user=self.user, room=self.room).delete()
                    RoomSubscription.objects.create(
                        user=self.user, room=self.room, is_notified=is_notified,
                    )
                    participants = MagicMock()
                    participants.__iter__.return_value = iter(
                        [] if is_chat_member else [SimpleNamespace(id=123, bot=False)],
                    )
                    participants.__len__.return_value = int(not is_chat_member)
                    participants.total = int(not is_chat_member)
                    change_membership = RoomSubscription.join_chat if is_chat_member else RoomSubscription.leave_chat

                    with patch("rooms.management.commands.recalculate_chat_members.TelegramClient") as client:
                        client.return_value.get_participants.side_effect = lambda *args, **kwargs: (
                            change_membership(self.user, self.room), participants,
                        )[1]
                        call_command("recalculate_chat_members", stdout=StringIO())

                    subscription = RoomSubscription.get(self.user, self.room)
                    self.assertEqual(subscription.is_chat_member, is_chat_member)
                    self.assertEqual(subscription.is_notified, is_notified)

    def test_sync_does_not_recreate_membership_after_leave_during_fetch(self):
        participants = MagicMock()
        participants.__iter__.return_value = iter([SimpleNamespace(id=123, bot=False)])
        participants.__len__.return_value = 1
        participants.total = 1

        with patch("rooms.management.commands.recalculate_chat_members.TelegramClient") as client:
            client.return_value.get_participants.side_effect = lambda *args, **kwargs: (
                RoomSubscription.leave_chat(self.user, self.room), participants,
            )[1]
            call_command("recalculate_chat_members", stdout=StringIO())

        subscription = RoomSubscription.get(self.user, self.room)
        self.assertFalse(subscription.is_chat_member)
        self.assertFalse(subscription.is_notified)

    def test_incomplete_or_failed_fetch_preserves_membership(self):
        RoomSubscription.join_chat(self.user, self.room)
        participants = MagicMock()
        participants.__len__.return_value = 0
        participants.total = 10

        for result in [participants, ValueError("Chat unavailable")]:
            with self.subTest(result=result):
                with patch("rooms.management.commands.recalculate_chat_members.TelegramClient") as client:
                    if isinstance(result, Exception):
                        client.return_value.get_participants.side_effect = result
                    else:
                        client.return_value.get_participants.return_value = result

                    with self.assertRaises(CommandError):
                        call_command("recalculate_chat_members", retries=0, stdout=StringIO())

                self.assertTrue(RoomSubscription.get(self.user, self.room).is_chat_member)

    def test_retry_recovers_without_rescanning_successful_rooms(self):
        other_room = Room.objects.create(slug="retry-room", title="Retry", color="#333", chat_id="-100456")
        participants = MagicMock()
        participants.__iter__.side_effect = lambda: iter([SimpleNamespace(id=123, bot=False)])
        participants.__len__.return_value = 1
        participants.total = 1

        with patch("rooms.management.commands.recalculate_chat_members.TelegramClient") as client, \
                patch("rooms.management.commands.recalculate_chat_members.time.sleep") as sleep:
            client.return_value.get_participants.side_effect = [participants, OSError("Disconnected"), participants]
            call_command("recalculate_chat_members", stdout=StringIO())

        self.assertEqual(client.return_value.get_participants.call_count, 3)
        calls = client.return_value.get_participants.call_args_list
        self.assertEqual(calls[2], calls[1])
        sleep.assert_called_once_with(60)
        self.assertTrue(RoomSubscription.get(self.user, self.room).is_chat_member)
        self.assertTrue(RoomSubscription.get(self.user, other_room).is_chat_member)

    def test_retry_exhaustion_preserves_membership_and_preferences(self):
        RoomSubscription.join_chat(self.user, self.room)
        RoomSubscription.subscribe(self.user, self.room)

        with patch("rooms.management.commands.recalculate_chat_members.TelegramClient") as client, \
                patch("rooms.management.commands.recalculate_chat_members.time.sleep") as sleep:
            client.return_value.get_participants.side_effect = ValueError("Chat unavailable")

            with self.assertRaises(CommandError):
                call_command("recalculate_chat_members", stdout=StringIO())

        self.assertEqual(client.return_value.get_participants.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [60, 120])
        subscription = RoomSubscription.get(self.user, self.room)
        self.assertTrue(subscription.is_chat_member)
        self.assertTrue(subscription.is_notified)

    def test_long_flood_wait_is_respected_before_retry(self):
        from telethon.errors import FloodWaitError

        participants = MagicMock()
        participants.__len__.return_value = 0
        participants.total = 0

        with patch("rooms.management.commands.recalculate_chat_members.TelegramClient") as client, \
                patch("rooms.management.commands.recalculate_chat_members.time.sleep") as sleep:
            client.return_value.get_participants.side_effect = [
                FloodWaitError(request=None, capture=300), participants,
            ]
            call_command("recalculate_chat_members", retry_delay=0, stdout=StringIO())

        self.assertEqual(sleep.call_args_list[0].args, (301,))
        self.assertEqual(client.return_value.get_participants.call_count, 2)
