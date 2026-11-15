import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from django.test import TransactionTestCase
from telegram.constants import ChatMemberStatus

from bot.handlers.membership import chat_membership, welcome_member
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

    def test_welcome_only_on_joining_registered_chat(self):
        for old_status, old_present, new_status, new_present, chat_id, user_id, is_bot, expected in (
            ("left", False, "member", True, -100123, 123, False, True),
            ("kicked", False, "member", True, -100123, 123, False, True),
            ("restricted", False, "restricted", True, -100123, 123, False, True),
            ("member", True, "administrator", True, -100123, 123, False, False),
            ("restricted", True, "member", True, -100123, 123, False, False),
            ("member", True, "left", False, -100123, 123, False, False),
            ("left", False, "restricted", False, -100123, 123, False, False),
            ("left", False, "member", True, -100999, 123, False, False),
            ("left", False, "member", True, -100123, 999, False, True),
            ("left", False, "member", True, -100123, 123, True, False),
        ):
            with self.subTest(old_status=old_status, new_status=new_status, chat_id=chat_id,
                              user_id=user_id, is_bot=is_bot, old_present=old_present):
                update = SimpleNamespace(chat_member=SimpleNamespace(
                    chat=SimpleNamespace(id=chat_id, type="supergroup"),
                    from_user=SimpleNamespace(id=user_id, is_bot=False),
                    invite_link=None, via_join_request=False, via_chat_folder_invite_link=False,
                    old_chat_member=SimpleNamespace(status=old_status, is_member=old_present),
                    new_chat_member=SimpleNamespace(
                        status=new_status, is_member=new_present,
                        user=SimpleNamespace(id=user_id, is_bot=is_bot, full_name="Newcomer", username=None),
                    ),
                ))
                bot = SimpleNamespace(send_message=AsyncMock())

                asyncio.run(welcome_member(update, SimpleNamespace(bot=bot)))

                self.assertEqual(bot.send_message.await_count, int(expected))

                if expected:
                    self.assertEqual(bot.send_message.await_args.kwargs["chat_id"], chat_id)
                    if user_id == 123:
                        self.assertIn(f"/user/{self.user.slug}/", bot.send_message.await_args.kwargs["text"])
                    self.assertNotIn("message_thread_id", bot.send_message.await_args.kwargs)

    def test_unknown_newcomer_invitation_routing(self):
        for actor_id, link, request, folder, template in (
            (999, None, False, False, "chat_welcome_unknown.html"),
            (123, None, False, False, "chat_welcome_invited.html"),
            (456, None, False, False, "chat_welcome_unknown_inviter.html"),
            (123, object(), False, False, "chat_welcome_unknown.html"),
            (123, None, True, False, "chat_welcome_unknown.html"),
            (123, None, False, True, "chat_welcome_unknown.html"),
        ):
            with self.subTest(actor_id=actor_id, link=link, request=request, folder=folder):
                update = SimpleNamespace(chat_member=SimpleNamespace(
                    chat=SimpleNamespace(id=-100123, type="supergroup"),
                    old_chat_member=SimpleNamespace(status="left"),
                    new_chat_member=SimpleNamespace(
                        status="member",
                        user=SimpleNamespace(id=999, is_bot=False, full_name="Guest", username="guest"),
                    ),
                    from_user=SimpleNamespace(id=actor_id, is_bot=False, full_name="Inviter", username=None),
                    invite_link=link, via_join_request=request, via_chat_folder_invite_link=folder,
                ))
                bot = SimpleNamespace(send_message=AsyncMock())

                with patch("bot.handlers.membership.render_to_string", return_value="Welcome") as render:
                    asyncio.run(welcome_member(update, SimpleNamespace(bot=bot)))

                self.assertEqual(render.call_args.args[0], f"notifications/telegram/membership/{template}")
                data = render.call_args.args[1]
                self.assertEqual(data["telegram_user"].id, 999)

                if template == "chat_welcome_invited.html":
                    self.assertEqual(data["inviter"], self.user)

                bot.send_message.assert_awaited_once()

    def test_welcome_links_each_person_by_club_profile_or_telegram_id(self):
        inviter = create_approved_user("webhook-inviter")
        inviter.telegram_id = "321"
        inviter.save()
        club_users = {123: self.user, 321: inviter}

        for newcomer_id, inviter_id in ((123, 456), (999, 123), (999, 456), (123, 123), (123, 321)):
            for username in (None, "guest"):
                with self.subTest(newcomer_id=newcomer_id, inviter_id=inviter_id, username=username):
                    update = SimpleNamespace(chat_member=SimpleNamespace(
                        chat=SimpleNamespace(id=-100123, type="supergroup"),
                        old_chat_member=SimpleNamespace(status="left"),
                        new_chat_member=SimpleNamespace(
                            status="member",
                            user=SimpleNamespace(
                                id=newcomer_id, is_bot=False, full_name="Guest <&>", username=username,
                            ),
                        ),
                        from_user=SimpleNamespace(id=inviter_id, is_bot=False, full_name="Inviter <&>", username=None),
                        invite_link=None, via_join_request=False, via_chat_folder_invite_link=False,
                    ))
                    bot = SimpleNamespace(send_message=AsyncMock())

                    asyncio.run(welcome_member(update, SimpleNamespace(bot=bot)))

                    bot.send_message.assert_awaited_once()
                    text = bot.send_message.await_args.kwargs["text"]

                    for telegram_id in {newcomer_id, inviter_id}:
                        if telegram_id in club_users:
                            self.assertIn(f"/user/{club_users[telegram_id].slug}/", text)
                            self.assertNotIn(f'href="tg://user?id={telegram_id}"', text)
                        else:
                            self.assertIn(f'href="tg://user?id={telegram_id}"', text)

                    self.assertNotIn("<&>", text)

                    if username:
                        self.assertIn("@guest", text)
