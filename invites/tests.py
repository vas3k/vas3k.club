from datetime import datetime, timedelta

import django
from django.test import TestCase
from django.urls import reverse
from django_q import brokers
from django_q.signing import SignedPackage

django.setup()  # todo: how to run tests from PyCharm without this workaround?

from authn.models.session import Code, Session
from debug.helpers import HelperClient
from invites.models import Invite
from payments.models import Payment
from payments.products import PRODUCTS
from users.models.user import User


class ActivateInviteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.invite_owner = User.objects.create(
            email="owner@test.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=365),
            slug="owner",
            moderation_status=User.MODERATION_STATUS_APPROVED,
        )
        cls.existing_victim = User.objects.create(
            email="victim@test.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            slug="victim",
            moderation_status=User.MODERATION_STATUS_APPROVED,
        )
        cls.payment = Payment.create(
            reference="test-invite-ref",
            user=cls.invite_owner,
            product=PRODUCTS["club1_invite"],
            status=Payment.STATUS_SUCCESS,
        )
        cls.invite = Invite.objects.create(
            user=cls.invite_owner,
            payment=cls.payment,
        )

        cls.broker = brokers.get_broker()
        cls.assertTrue(cls.broker.ping(), "broker is not available")

    def setUp(self):
        self.client = HelperClient(user=self.existing_victim)
        self.broker.purge_queue()
        self.invite.used_at = None
        self.invite.invited_user = None
        self.invite.save()

    def test_anonymous_with_existing_email_does_not_get_session(self):
        sessions_before = Session.objects.filter(user=self.existing_victim).count()

        response = self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": self.existing_victim.email},
        )

        self.assertFalse(self.client.is_authorised())

        sessions_after = Session.objects.filter(user=self.existing_victim).count()
        self.assertEqual(sessions_before, sessions_after)

        code = Code.objects.filter(recipient=self.existing_victim.email).first()
        self.assertIsNotNone(code)

        self.assertContains(response, "Вам отправлен код!", status_code=200)

        queued_func_names = set()
        while True:
            packages = self.broker.dequeue()
            if not packages:
                break
            task_signed = packages[0][1]
            task = SignedPackage.loads(task_signed)
            queued_func_names.add(task["func"].__name__)
        self.assertIn("send_auth_email", queued_func_names)

    def test_anonymous_with_new_email_does_not_get_session(self):
        new_email = "brandnew@test.com"
        self.assertFalse(User.objects.filter(email=new_email).exists())

        response = self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": new_email},
        )

        new_user = User.objects.filter(email=new_email).first()
        self.assertIsNotNone(new_user)

        self.assertFalse(self.client.is_authorised())

        code = Code.objects.filter(recipient=new_email).first()
        self.assertIsNotNone(code)

        self.assertContains(response, "Вам отправлен код!", status_code=200)

    def test_authenticated_user_activates_on_own_account(self):
        self.client.authorise()

        response = self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": self.existing_victim.email},
        )

        self.assertRedirects(
            response,
            expected_url=f"/user/{self.existing_victim.slug}/",
            fetch_redirect_response=False,
        )

        self.invite.refresh_from_db()
        self.assertIsNotNone(self.invite.used_at)
        self.assertEqual(self.invite.invited_user, self.existing_victim)

    def test_anonymous_does_not_activate_invite_or_subscription(self):
        expires_before = User.objects.get(id=self.existing_victim.id).membership_expires_at

        self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": self.existing_victim.email},
        )

        self.existing_victim.refresh_from_db()
        self.assertEqual(self.existing_victim.membership_expires_at, expires_before)

        self.invite.refresh_from_db()
        self.assertIsNone(self.invite.used_at)

    def test_authenticated_with_different_email_requires_verification(self):
        self.client.authorise()

        other_email = self.invite_owner.email
        expires_before = User.objects.get(id=self.invite_owner.id).membership_expires_at
        sessions_before = Session.objects.filter(user=self.invite_owner).count()

        response = self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": other_email},
        )

        sessions_after = Session.objects.filter(user=self.invite_owner).count()
        self.assertEqual(sessions_before, sessions_after)

        self.invite.refresh_from_db()
        self.assertIsNone(self.invite.used_at)

        self.invite_owner.refresh_from_db()
        self.assertEqual(self.invite_owner.membership_expires_at, expires_before)

        code = Code.objects.filter(recipient=other_email).first()
        self.assertIsNotNone(code)

        self.assertContains(response, "Вам отправлен код!", status_code=200)
