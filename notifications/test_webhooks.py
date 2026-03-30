import json
from urllib.parse import urlencode

from django.test import TestCase, override_settings
from django.urls import reverse

from notifications.models import WebhookEvent


VALID_SECRET = "test-webhook-secret-abc123"


class WebhookTestMixin:

    def _webhook_url(self, event_type="email_bounce", secret=None):
        url = reverse("webhook_event", kwargs={"event_type": event_type})
        if secret is not None:
            url += f"?{urlencode({'secret': secret})}"
        return url

    def _post_webhook(self, event_type="email_bounce", data=None, secret=VALID_SECRET):
        return self.client.post(
            self._webhook_url(event_type=event_type, secret=secret),
            data=json.dumps(data if data is not None else {}),
            content_type="application/json",
        )


@override_settings(WEBHOOK_SECRETS={VALID_SECRET})
class WebhookAuthTest(WebhookTestMixin, TestCase):

    def test_valid_secret_accepts_request(self):
        response = self._post_webhook(data={"bounce": {"type": "Permanent"}})

        self.assertEqual(response.status_code, 200)

    def test_missing_secret_is_forbidden(self):
        response = self._post_webhook(secret=None)

        self.assertEqual(response.status_code, 403)

    def test_empty_secret_is_forbidden(self):
        response = self._post_webhook(secret="")

        self.assertEqual(response.status_code, 403)

    def test_wrong_secret_is_forbidden(self):
        response = self._post_webhook(secret="wrong-secret")

        self.assertEqual(response.status_code, 403)

    def test_get_method_not_allowed(self):
        response = self.client.get(self._webhook_url(secret=VALID_SECRET))

        self.assertEqual(response.status_code, 405)

    def test_no_event_stored_on_auth_failure(self):
        self._post_webhook(
            data={"bounce": {"type": "Permanent"}},
            secret="wrong",
        )

        self.assertEqual(WebhookEvent.objects.count(), 0)


@override_settings(WEBHOOK_SECRETS={"secret-one", "secret-two"})
class WebhookMultipleSecretsTest(WebhookTestMixin, TestCase):

    def test_first_secret_accepted(self):
        self.assertEqual(self._post_webhook(secret="secret-one").status_code, 200)

    def test_second_secret_accepted(self):
        self.assertEqual(self._post_webhook(secret="secret-two").status_code, 200)

    def test_unknown_secret_rejected(self):
        self.assertEqual(self._post_webhook(secret="secret-three").status_code, 403)


@override_settings(WEBHOOK_SECRETS=set())
class WebhookEmptySecretsTest(WebhookTestMixin, TestCase):

    def test_rejects_any_secret(self):
        self.assertEqual(self._post_webhook(secret="anything").status_code, 403)

    def test_rejects_empty_secret(self):
        self.assertEqual(self._post_webhook(secret="").status_code, 403)


@override_settings(WEBHOOK_SECRETS={VALID_SECRET})
class WebhookBodyParsingTest(WebhookTestMixin, TestCase):

    def _post_raw(self, body):
        return self.client.post(
            self._webhook_url(secret=VALID_SECRET),
            data=body,
            content_type="application/json",
        )

    def test_invalid_json_returns_400(self):
        response = self._post_raw("not-json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(WebhookEvent.objects.count(), 0)

    def test_empty_body_returns_400(self):
        response = self._post_raw("")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(WebhookEvent.objects.count(), 0)


@override_settings(WEBHOOK_SECRETS={VALID_SECRET})
class WebhookEventRoutingTest(WebhookTestMixin, TestCase):

    def test_email_bounce_event_stored(self):
        self._post_webhook("email_bounce", {"bounceType": "Permanent"})

        event = WebhookEvent.objects.get()
        self.assertEqual(event.type, "email_bounce")
        self.assertEqual(event.data["bounceType"], "Permanent")
        self.assertIsNone(event.recipient)

    def test_email_complaint_event_stored(self):
        self._post_webhook("email_complaint", {"reason": "spam"})

        event = WebhookEvent.objects.get()
        self.assertEqual(event.type, "email_complaint")
        self.assertEqual(event.data["reason"], "spam")

    def test_unknown_event_type_uses_default_handler(self):
        self._post_webhook("some_future_event", {"key": "value"})

        event = WebhookEvent.objects.get()
        self.assertEqual(event.type, "some_future_event")
        self.assertEqual(event.data["key"], "value")

    def test_json_data_preserved_exactly(self):
        payload = {
            "nested": {"list": [1, 2, 3], "null": None},
            "unicode": "тест",
        }
        self._post_webhook("email_bounce", payload)

        event = WebhookEvent.objects.get()
        self.assertEqual(event.data, payload)
