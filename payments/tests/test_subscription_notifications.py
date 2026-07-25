from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from django.core.management import call_command
from django.test import TestCase

from users.models.user import User

COMMAND = "payments.management.commands.send_subscription_notifications"


class SubscriptionNotificationTest(TestCase):
    def create_user(self, slug: str, expires_at: datetime, **kwargs):
        membership_platform_type = kwargs.pop(
            "membership_platform_type",
            User.MEMBERSHIP_PLATFORM_DIRECT,
        )
        return User.objects.create(
            slug=slug,
            email=f"{slug}@test.com",
            full_name=slug,
            membership_started_at=expires_at - timedelta(days=365),
            membership_expires_at=expires_at,
            membership_platform_type=membership_platform_type,
            moderation_status=User.MODERATION_STATUS_APPROVED,
            is_email_verified=True,
            **kwargs,
        )

    @patch(f"{COMMAND}.ban_user_in_all_chats")
    @patch(f"{COMMAND}.send_telegram_message")
    @patch(f"{COMMAND}.send_transactional_email")
    def test_expire_selects_only_exact_day_and_skips_patreon(
        self,
        send_email,
        send_telegram,
        _ban_user,
    ):
        today = date.today()
        selected = self.create_user(
            "selected",
            datetime.combine(today, datetime.min.time()).replace(hour=12),
            telegram_id="222",
        )
        self.create_user("day_before", datetime.combine(today - timedelta(days=1), datetime.min.time()))
        self.create_user("day_after", datetime.combine(today + timedelta(days=1), datetime.min.time()))
        self.create_user(
            "patreon",
            datetime.combine(today, datetime.min.time()).replace(hour=15),
            membership_platform_type=User.MEMBERSHIP_PLATFORM_PATREON,
            telegram_id="111",
        )

        call_command("send_subscription_notifications", production=True, stage="expire")

        emailed = [call.kwargs["recipient"] for call in send_email.call_args_list]
        telegram_chats = [call.kwargs["chat"].id for call in send_telegram.call_args_list]
        self.assertIn(selected.email, emailed)
        self.assertNotIn("day_before@test.com", emailed)
        self.assertNotIn("day_after@test.com", emailed)
        self.assertNotIn("patreon@test.com", emailed)
        self.assertIn("222", telegram_chats)
        self.assertNotIn("111", telegram_chats)

    @patch(f"{COMMAND}.ban_user_in_all_chats")
    @patch(f"{COMMAND}.send_telegram_message")
    @patch(f"{COMMAND}.send_transactional_email")
    def test_final_only_removes_from_chats(
        self,
        send_email,
        send_telegram,
        ban_user,
    ):
        expiration_day = date.today() - relativedelta(months=2)
        user = self.create_user(
            "final",
            datetime.combine(expiration_day, datetime.min.time()),
            telegram_id="123",
        )

        call_command("send_subscription_notifications", production=True, stage="final")

        send_email.assert_not_called()
        send_telegram.assert_not_called()
        ban_user.assert_called_once_with(user, is_permanent=False)

    @patch(f"{COMMAND}.ban_user_in_all_chats")
    @patch(f"{COMMAND}.send_telegram_message")
    @patch(f"{COMMAND}.send_transactional_email")
    def test_recurrent_subscriptions_are_skipped(self, send_email, send_telegram, ban_user):
        expiration_day = date.today() - relativedelta(months=2)
        self.create_user(
            "recurrent",
            datetime.combine(expiration_day, datetime.min.time()),
            telegram_id="123",
            membership_platform_data={"recurrent": True},
        )

        call_command("send_subscription_notifications", production=True, stage="final")

        send_email.assert_not_called()
        send_telegram.assert_not_called()
        ban_user.assert_not_called()

    @patch(f"{COMMAND}.get_user_chats")
    @patch(f"{COMMAND}.send_telegram_message")
    @patch(f"{COMMAND}.send_transactional_email")
    def test_expire_lists_chats_when_there_are_at_least_three(
        self,
        send_email,
        send_telegram,
        get_user_chats,
    ):
        today = date.today()
        self.create_user(
            "expire_chats",
            datetime.combine(today, datetime.min.time()),
            telegram_id="123",
        )
        get_user_chats.return_value = [
            SimpleNamespace(chat_name="Чат А", icon="🅰️"),
            SimpleNamespace(chat_name="Чат Б", icon="🅱️"),
            SimpleNamespace(chat_name="Чат В", icon="©️"),
        ]

        call_command("send_subscription_notifications", production=True, stage="expire")

        body = send_email.call_args.kwargs["html"]
        self.assertIn("Чат А", body)
        self.assertIn("Чат Б", body)
        self.assertIn("Чат В", body)
        self.assertIn("🅰️", body)

    @patch(f"{COMMAND}.get_user_chats")
    @patch(f"{COMMAND}.send_telegram_message")
    @patch(f"{COMMAND}.send_transactional_email")
    def test_expire_hides_chat_list_when_fewer_than_three(
        self,
        send_email,
        send_telegram,
        get_user_chats,
    ):
        today = date.today()
        self.create_user(
            "expire_few_chats",
            datetime.combine(today, datetime.min.time()),
            telegram_id="123",
        )
        get_user_chats.return_value = [
            SimpleNamespace(chat_name="Чат А", icon="🅰️"),
            SimpleNamespace(chat_name="Чат Б", icon="🅱️"),
        ]

        call_command("send_subscription_notifications", production=True, stage="expire")

        body = send_email.call_args.kwargs["html"]
        self.assertNotIn("Чат А", body)
        self.assertNotIn("Например вот из этих", body)

    @patch(f"{COMMAND}.get_user_chats")
    @patch(f"{COMMAND}.send_telegram_message")
    @patch(f"{COMMAND}.send_transactional_email")
    def test_expire_limits_rooms_list_to_ten(
        self,
        send_email,
        send_telegram,
        get_user_chats,
    ):
        today = date.today()
        self.create_user(
            "expire_many_chats",
            datetime.combine(today, datetime.min.time()),
            telegram_id="123",
        )
        get_user_chats.return_value = [
            SimpleNamespace(chat_name=f"Чат {i}", icon=None)
            for i in range(12)
        ]

        call_command("send_subscription_notifications", production=True, stage="expire")

        body = send_email.call_args.kwargs["html"]
        self.assertIn("Чат 0", body)
        self.assertIn("Чат 9", body)
        self.assertNotIn("Чат 10", body)
        self.assertNotIn("Чат 11", body)
