import asyncio
import os
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TransactionTestCase
from telegram.constants import ChatMemberStatus

from bot.handlers.membership import chat_membership
from debug.utils_for_tests import create_approved_user
from rooms.models import Room, RoomSubscription


@patch.dict(os.environ, {"DJANGO_ALLOW_ASYNC_UNSAFE": "true"})
class TestChatMembership(TransactionTestCase):
    def setUp(self):
        self.user = create_approved_user("webhook-member")
        self.user.telegram_id = "123"
        self.user.save()
        self.room = Room.objects.create(slug="webhook-room", title="Chat", color="#333", chat_id="-100123")

    def test_membership_updates_preserve_notification_preferences(self):
        for is_notified in [True, False]:
            subscription, created = RoomSubscription.objects.update_or_create(
                user=self.user, room=self.room, defaults={"is_notified": is_notified},
            )
            created_at = subscription.created_at

            for status, is_chat_member in [
                (ChatMemberStatus.MEMBER, True),
                (ChatMemberStatus.ADMINISTRATOR, True),
                (ChatMemberStatus.RESTRICTED, True),
                (ChatMemberStatus.RESTRICTED, False),
                (ChatMemberStatus.LEFT, False),
                (ChatMemberStatus.BANNED, False),
                (ChatMemberStatus.MEMBER, True),
            ]:
                with self.subTest(status=status, is_chat_member=is_chat_member, is_notified=is_notified):
                    member = SimpleNamespace(
                        user=SimpleNamespace(id=123, is_bot=False), status=status, is_member=is_chat_member,
                    )
                    update = SimpleNamespace(chat_member=SimpleNamespace(
                        new_chat_member=member, chat=SimpleNamespace(id=-100123),
                    ))

                    asyncio.run(chat_membership(update, SimpleNamespace()))

                    subscription.refresh_from_db()
                    self.assertEqual(subscription.is_chat_member, is_chat_member)
                    self.assertEqual(subscription.is_notified, is_notified)
                    self.assertEqual(subscription.created_at, created_at)

    def test_unknown_user_is_ignored(self):
        member = SimpleNamespace(user=SimpleNamespace(id=999, is_bot=False), status=ChatMemberStatus.MEMBER)
        update = SimpleNamespace(chat_member=SimpleNamespace(
            new_chat_member=member, chat=SimpleNamespace(id=-100123),
        ))

        asyncio.run(chat_membership(update, SimpleNamespace()))

        self.assertFalse(RoomSubscription.objects.exists())
