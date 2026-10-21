from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import TestCase

from club.exceptions import BadRequest
from payments.helpers import extend_membership, cancel_all_stripe_subscriptions
from users.models.user import User


def _create_user(slug, days_left):
    return User.objects.create(
        slug=slug,
        email=f"{slug}@test.com",
        full_name=slug,
        membership_started_at=datetime.utcnow() - timedelta(days=30),
        membership_expires_at=datetime.utcnow() + timedelta(days=days_left),
        moderation_status=User.MODERATION_STATUS_APPROVED,
        is_email_verified=True,
    )


class TestExtendMembership(TestCase):
    def test_extension_starts_now_for_expired_member(self):
        user = _create_user("extend_expired", days_left=-5)

        result = extend_membership(days=10, user=user)

        user.refresh_from_db()
        self.assertEqual(result, user.membership_expires_at)
        self.assertEqual(user.membership_platform_type, User.MEMBERSHIP_PLATFORM_DIRECT)
        self.assertAlmostEqual(result, datetime.utcnow() + timedelta(days=10), delta=timedelta(seconds=2))

    def test_extension_adds_to_existing_membership_without_debiting_others(self):
        user = _create_user("extend_active", days_left=30)
        other = _create_user("extend_other", days_left=120)
        user_before = user.membership_expires_at
        other_before = other.membership_expires_at

        extend_membership(days=7, user=user)

        user.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(user.membership_expires_at, user_before + timedelta(days=7))
        self.assertEqual(other.membership_expires_at, other_before)

    def test_non_positive_extension_leaves_membership_unchanged(self):
        user = _create_user("extend_invalid", days_left=30)
        before = user.membership_expires_at

        for days in [0, -1]:
            with self.subTest(days=days):
                with self.assertRaises(BadRequest):
                    extend_membership(days=days, user=user)

                user.refresh_from_db()
                self.assertEqual(user.membership_expires_at, before)


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
