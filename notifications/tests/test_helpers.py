from unittest.mock import patch

from django.conf import settings
from django.test import TestCase

from debug.utils_for_tests import create_approved_user
from notifications.helpers import generate_notification_token, verify_notification_token


class NotificationTokenTest(TestCase):
    def setUp(self):
        self.user = create_approved_user("token_user")
        self.other = create_approved_user("token_other")

    def _token(self, user=None):
        user = user or self.user
        token = generate_notification_token(user)
        self.assertNotIn(user.secret_hash, token)
        self.assertNotIn(self.user.secret_hash, token)
        self.assertNotIn(self.other.secret_hash, token)
        return token

    def test_generated_token_verifies_for_same_user(self):
        token = self._token()
        self.assertTrue(verify_notification_token(self.user, token))

    def test_token_does_not_verify_for_another_user(self):
        token = self._token()
        self.assertFalse(verify_notification_token(self.other, token))

    def test_tokens_from_different_seconds_are_different(self):
        with patch("django.core.signing.time.time", return_value=1_700_000_000):
            first = self._token()
        with patch("django.core.signing.time.time", return_value=1_700_000_001):
            second = self._token()

        self.assertNotEqual(first, second)
        with patch("django.core.signing.time.time", return_value=1_700_000_001):
            self.assertTrue(verify_notification_token(self.user, first))
            self.assertTrue(verify_notification_token(self.user, second))

    def test_malformed_and_tampered_tokens_are_rejected(self):
        self.assertFalse(verify_notification_token(self.user, "not-a-token"))
        self.assertFalse(verify_notification_token(self.user, self.user.secret_hash))
        self.assertFalse(verify_notification_token(self.user, ""))
        self.assertFalse(verify_notification_token(self.user, None))

        token = self._token()
        tampered = token[:-1] + ("x" if token[-1] != "x" else "y")
        self.assertFalse(verify_notification_token(self.user, tampered))

    def test_rotating_secret_hash_invalidates_token(self):
        token = self._token()
        self.user.secret_hash = "rotated" + self.user.secret_hash[7:]
        self.assertNotIn(self.user.secret_hash, token)
        self.assertFalse(verify_notification_token(self.user, token))

    def test_token_expires_after_max_age(self):
        now = 1_700_000_000
        with patch("django.core.signing.time.time", return_value=now):
            token = self._token()

        with patch("django.core.signing.time.time", return_value=now + settings.NOTIFICATION_TOKEN_EXPIRATION_TIMEDELTA.total_seconds() - 1):
            self.assertTrue(verify_notification_token(self.user, token))

        with patch("django.core.signing.time.time", return_value=now + settings.NOTIFICATION_TOKEN_EXPIRATION_TIMEDELTA.total_seconds() + 1):
            self.assertFalse(verify_notification_token(self.user, token))
