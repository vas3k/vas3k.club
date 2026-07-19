from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.test import TestCase

from club.exceptions import BadRequest, InsufficientFunds
from payments.helpers import gift_membership_days, cancel_all_stripe_subscriptions
from users.models.user import User


def _create_user(slug, days_left):
    return User.objects.create(
        slug=slug,
        email=f"{slug}@test.com",
        full_name=slug,
        membership_started_at=datetime.now(timezone.utc) - timedelta(days=30),
        membership_expires_at=datetime.now(timezone.utc) + timedelta(days=days_left),
        moderation_status=User.MODERATION_STATUS_APPROVED,
        is_email_verified=True,
    )


class TestGiftMembershipDays(TestCase):
    def test_extends_expired_user_and_deducts_from_sender(self):
        from_user = _create_user("gift_from", days_left=120)
        to_user = _create_user("gift_to", days_left=-5)
        from_before = from_user.membership_expires_at

        result = gift_membership_days(days=10, from_user=from_user, to_user=to_user)

        from_user.refresh_from_db()
        to_user.refresh_from_db()

        self.assertEqual(result, to_user.membership_expires_at)
        self.assertEqual(to_user.membership_platform_type, User.MEMBERSHIP_PLATFORM_DIRECT)
        self.assertGreater(to_user.membership_expires_at, datetime.now(timezone.utc) + timedelta(days=9))
        self.assertAlmostEqual(
            from_user.membership_expires_at,
            from_before - timedelta(days=10),
            delta=timedelta(seconds=2),
        )

    def test_does_not_deduct_if_disabled(self):
        from_user = _create_user("gift_from_no_deduct", days_left=120)
        to_user = _create_user("gift_to_no_deduct", days_left=1)
        from_before = from_user.membership_expires_at

        gift_membership_days(
            days=7,
            from_user=from_user,
            to_user=to_user,
            deduct_from_original_user=False,
        )

        from_user.refresh_from_db()
        self.assertEqual(from_user.membership_expires_at, from_before)

    def test_raises_insufficient_funds(self):
        from_user = _create_user("gift_from_low", days_left=3)
        to_user = _create_user("gift_to_low", days_left=30)

        with self.assertRaises(InsufficientFunds):
            gift_membership_days(days=5, from_user=from_user, to_user=to_user)

    def test_raises_bad_request_for_non_positive_days(self):
        from_user = _create_user("gift_from_zero", days_left=10)
        to_user = _create_user("gift_to_zero", days_left=10)

        with self.assertRaises(BadRequest):
            gift_membership_days(days=0, from_user=from_user, to_user=to_user)


class TestCancelAllStripeSubscriptions(TestCase):
    @patch("payments.helpers.stripe.Subscription.list")
    @patch("payments.helpers.stripe.Subscription.delete")
    def test_cancels_each_subscription_and_returns_true(self, mock_delete, mock_list):
        mock_list.return_value = {"data": [{"id": "sub_1"}, {"id": "sub_2"}]}

        result = cancel_all_stripe_subscriptions("cus_123")

        self.assertTrue(result)
        self.assertEqual(mock_delete.call_count, 2)

    def test_returns_false_without_stripe_id(self):
        self.assertFalse(cancel_all_stripe_subscriptions(""))
