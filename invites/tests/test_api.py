import json

from django.test import TestCase
from django.urls import reverse

from debug.utils_for_tests import create_approved_user, login
from invites.models import Invite
from payments.models import Payment


class TestInviteApi(TestCase):
    def setUp(self):
        self.admin = create_approved_user("api_invite_admin", roles=["god"])
        self.member = create_approved_user("api_invite_member")
        self.url = reverse("api_gift_invite_link")

    def test_admin_creates_invite_and_payment_from_json(self):
        login(self.client, self.admin)

        response = self.client.post(
            self.url, {"reference": "api-json-reference", "telegram_user_id": 123},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        invite = Invite.objects.select_related("payment").get()
        self.assertEqual(response.json()["invite"]["code"], invite.code)
        self.assertEqual(invite.user_id, self.admin.id)
        self.assertEqual(invite.payment.reference, "api-json-reference")
        self.assertEqual(invite.payment.status, Payment.STATUS_SUCCESS)
        self.assertEqual(json.loads(invite.payment.data)["telegram_user_id"], "123")

    def test_admin_creates_invite_from_form(self):
        login(self.client, self.admin)

        response = self.client.post(self.url, {"reference": "api-form-reference", "telegram_user_id": "456"})

        self.assertEqual(response.status_code, 200)
        invite = Invite.objects.select_related("payment").get()
        self.assertEqual(invite.payment.reference, "api-form-reference")
        self.assertEqual(json.loads(invite.payment.data)["telegram_user_id"], "456")

    def test_member_cannot_create_invites_or_payments(self):
        login(self.client, self.member)

        response = self.client.post(self.url, {"reference": "api-forbidden"}, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "api-access-denied")
        self.assertFalse(Invite.objects.exists())
        self.assertFalse(Payment.objects.exists())

    def test_invalid_json_does_not_create_invites_or_payments(self):
        login(self.client, self.admin)

        for body in ["", "{broken", "[]", "null", "42"]:
            with self.subTest(body=body):
                response = self.client.post(
                    self.url, body, content_type="application/json", CONTENT_TYPE="application/json",
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "bad-request")
                self.assertFalse(Invite.objects.exists())
                self.assertFalse(Payment.objects.exists())

    def test_unsupported_method_does_not_create_payments(self):
        login(self.client, self.admin)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 405)
        self.assertFalse(Invite.objects.exists())
        self.assertFalse(Payment.objects.exists())
