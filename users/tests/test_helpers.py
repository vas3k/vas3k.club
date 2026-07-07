from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import TestCase

from common.data.ban import BanReason
from users.helpers import calculate_progressive_ban_days, custom_ban_user
from users.models.user import User


def _create_user(slug, membership_days=30, metadata=None):
    return User.objects.create(
        slug=slug,
        email=f"{slug}@test.com",
        full_name=slug,
        membership_started_at=datetime.utcnow() - timedelta(days=30),
        membership_expires_at=datetime.utcnow() + timedelta(days=membership_days),
        moderation_status=User.MODERATION_STATUS_APPROVED,
        is_email_verified=True,
        metadata=metadata,
    )


class TestUserBanHelpers(TestCase):
    def test_calculate_progressive_ban_days_for_first_ban(self):
        user = _create_user("ban_first")

        days = calculate_progressive_ban_days(user, min_days=5)

        self.assertEqual(days, 5)

    def test_calculate_progressive_ban_days_uses_next_step(self):
        user = _create_user("ban_next", metadata={"last_ban": {"days": 3}})

        days = calculate_progressive_ban_days(user, min_days=2)

        self.assertEqual(days, 10)

    @patch("users.helpers.send_banned_email")
    @patch("users.helpers.notify_user_ban")
    @patch("users.helpers.notify_admins_on_ban")
    @patch("users.helpers.cancel_all_stripe_subscriptions")
    def test_custom_ban_cancels_subscription_for_long_bans(
        self,
        mock_cancel,
        mock_admins,
        mock_notify,
        mock_email,
    ):
        user = _create_user("ban_long", membership_days=5)
        reason = BanReason(name="spam", description="spammy")

        result = custom_ban_user(user=user, days=90, reason=reason)

        user.refresh_from_db()
        self.assertTrue(result)
        self.assertEqual(user.metadata["last_ban"]["days"], 90)
        self.assertEqual(user.metadata["last_ban"]["reason"], "spam")
        mock_email.assert_called_once()
        mock_notify.assert_called_once()
        mock_admins.assert_called_once()
        mock_cancel.assert_called_once_with(user.stripe_id)

    @patch("users.helpers.send_banned_email")
    @patch("users.helpers.notify_user_ban")
    @patch("users.helpers.notify_admins_on_ban")
    @patch("users.helpers.cancel_all_stripe_subscriptions")
    def test_custom_ban_does_not_cancel_subscription_for_short_bans(
        self,
        mock_cancel,
        mock_admins,
        mock_notify,
        mock_email,
    ):
        user = _create_user("ban_short", membership_days=300)
        reason = BanReason(name="flame", description="flame")

        result = custom_ban_user(user=user, days=10, reason=reason)

        self.assertTrue(result)
        mock_email.assert_called_once()
        mock_notify.assert_called_once()
        mock_admins.assert_called_once()
        mock_cancel.assert_not_called()
