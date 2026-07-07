from django.test import Client, TestCase
from django.urls import reverse

from debug.utils_for_tests import create_approved_user, login
from invites.models import Invite
from payments.models import Payment
from payments.products import PRODUCTS
from users.models.user import User


def _create_invite(user, reference):
    payment = Payment.create(
        reference=reference,
        user=user,
        product=PRODUCTS["club1_invite"],
        status=Payment.STATUS_SUCCESS,
    )
    return Invite.objects.create(user=user, payment=payment)


class TestInviteViews(TestCase):
    def setUp(self):
        self.owner = create_approved_user("invite_owner")
        self.viewer = create_approved_user("invite_viewer")
        self.invite = _create_invite(self.owner, "invite-view-ref")
        self.client = Client()

    def test_show_invite_uses_edit_template_for_owner(self):
        login(self.client, self.owner)

        response = self.client.get(reverse("show_invite", args=[self.invite.code]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "invites/edit.html")

    def test_show_invite_uses_public_template_for_other_user(self):
        login(self.client, self.viewer)

        response = self.client.get(reverse("show_invite", args=[self.invite.code]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "invites/show.html")

    def test_activate_invite_with_invalid_email_does_not_create_code(self):
        response = self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": "not-an-email"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "error.html")
        self.invite.refresh_from_db()
        self.assertIsNone(self.invite.used_at)

    def test_godmode_generate_invite_code_creates_invite(self):
        god = create_approved_user("invite_god", roles=[User.ROLE_GOD])
        login(self.client, god)

        before = Invite.objects.filter(user=god).count()
        response = self.client.post(reverse("godmode_generate_invite_code"))
        after = Invite.objects.filter(user=god).count()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("invites"))
        self.assertEqual(after, before + 1)
