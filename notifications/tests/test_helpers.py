from unittest.mock import patch

from django.test import TestCase

from debug.utils_for_tests import create_approved_user
from notifications.helpers import generate_notification_token, verify_notification_token


class NotificationTokenTest(TestCase):
    def setUp(self):
        self.user = create_approved_user("token_user")
        self.other = create_approved_user("token_other")

    def test_generated_token_verifies_for_same_user(self):
        token = generate_notification_token(self.user)
        self.assertTrue(verify_notification_token(self.user, token))

    def test_token_does_not_verify_for_another_user(self):
        token = generate_notification_token(self.user)
        self.assertFalse(verify_notification_token(self.other, token))

    def test_tokens_from_different_seconds_are_different(self):
        with patch("notifications.helpers.time.time", return_value=1_700_000_000):
            first = generate_notification_token(self.user)
        with patch("notifications.helpers.time.time", return_value=1_700_000_001):
            second = generate_notification_token(self.user)

        self.assertNotEqual(first, second)
        self.assertTrue(verify_notification_token(self.user, first))
        self.assertTrue(verify_notification_token(self.user, second))

    def test_malformed_and_tampered_tokens_are_rejected(self):
        self.assertFalse(verify_notification_token(self.user, "not-a-token"))
        self.assertFalse(verify_notification_token(self.user, self.user.secret_hash))

        token = generate_notification_token(self.user)
        timestamp, signature = token.split(".", 1)
        self.assertFalse(verify_notification_token(self.user, f"{timestamp}.{signature[:-1]}x"))
