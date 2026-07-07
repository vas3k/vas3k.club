import base64
import hashlib
import hmac
import json
from unittest.mock import patch

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from club.exceptions import NotFound
from debug.utils_for_tests import create_approved_user, login
from users.models.user import User


def _telegram_hash(data, token):
    payload = dict(data)
    payload.pop("hash", None)
    check_string = "\n".join(sorted([f"{k}={v}" for k, v in payload.items()]))
    secret_key = hashlib.sha256(token.encode()).digest()
    return hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()


@override_settings(TELEGRAM_TOKEN="test-telegram-token")
class TestNotificationViews(TestCase):
    def setUp(self):
        self.user = create_approved_user("notify_user", is_email_verified=False, is_email_unsubscribed=False)
        self.client = Client()

    def test_email_confirm_accepts_base64_secret(self):
        secret_b64 = base64.b64encode(self.user.secret_hash.encode()).decode()

        response = self.client.get(reverse("email_confirm", args=[self.user.id, secret_b64]))

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

    def test_email_unsubscribe_sets_flags(self):
        response = self.client.get(reverse("email_unsubscribe", args=[self.user.id, self.user.secret_hash]))

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_unsubscribed)
        self.assertEqual(self.user.email_digest_type, User.EMAIL_DIGEST_TYPE_NOPE)

    def test_email_digest_switch_to_daily_resets_unsubscribed(self):
        self.user.is_email_unsubscribed = True
        self.user.email_digest_type = User.EMAIL_DIGEST_TYPE_NOPE
        self.user.save(update_fields=["is_email_unsubscribed", "email_digest_type"])

        response = self.client.get(
            reverse("email_digest_switch", args=[User.EMAIL_DIGEST_TYPE_DAILY, self.user.id, self.user.secret_hash])
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_email_unsubscribed)
        self.assertEqual(self.user.email_digest_type, User.EMAIL_DIGEST_TYPE_DAILY)

    def test_email_digest_switch_invalid_type_returns_404(self):
        response = self.client.get(reverse("email_digest_switch", args=["invalid", self.user.id, self.user.secret_hash]))
        self.assertEqual(response.status_code, 404)

    def test_link_telegram_persists_id_and_clears_cache_key(self):
        login(self.client, self.user)
        payload = {
            "id": "123456",
            "username": "teleuser",
            "first_name": "Test",
            "last_name": "User",
        }
        payload["hash"] = _telegram_hash(payload, settings.TELEGRAM_TOKEN)

        response = self.client.post(
            reverse("link_telegram"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.telegram_id, "123456")
        self.assertEqual(self.user.telegram_data["username"], "teleuser")

    def test_link_telegram_invalid_signature_is_forbidden(self):
        login(self.client, self.user)
        payload = {
            "id": "123456",
            "username": "teleuser",
            "hash": "invalid",
        }

        response = self.client.post(
            reverse("link_telegram"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_link_telegram_malformed_json_returns_400(self):
        login(self.client, self.user)

        response = self.client.post(
            reverse("link_telegram"),
            data="{broken json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_link_telegram_empty_body_returns_400(self):
        login(self.client, self.user)

        response = self.client.post(
            reverse("link_telegram"),
            data="",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_render_weekly_digest_returns_html(self):
        with patch("notifications.views.generate_weekly_digest", return_value=("<h1>Digest</h1>", None)):
            response = self.client.get(reverse("render_weekly_digest"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("Digest", response.content.decode())

    def test_render_weekly_digest_404_when_not_found(self):
        with patch("notifications.views.generate_weekly_digest", side_effect=NotFound()):
            response = self.client.get(reverse("render_weekly_digest"))

        self.assertEqual(response.status_code, 404)
