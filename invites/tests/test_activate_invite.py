from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse
from django_q import brokers
from django_q.signing import SignedPackage

from authn.models.session import Code, Session
from debug.helpers import HelperClient
from invites.models import INVITE_EXPIRATION_DAYS, Invite
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
        self.assertAlmostEqual(
            new_user.membership_expires_at,
            datetime.utcnow() + timedelta(days=1),
            delta=timedelta(seconds=5),
        )

        self.assertFalse(self.client.is_authorised())

        code = Code.objects.filter(recipient=new_email).first()
        self.assertIsNotNone(code)

        self.assertContains(response, "Вам отправлен код!", status_code=200)

    def test_anonymous_new_user_activates_after_email_code(self):
        new_email = "newbie@test.com"
        self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": new_email},
        )
        code = Code.objects.filter(recipient=new_email).first()
        self.assertIsNotNone(code)

        goto = reverse("show_invite", kwargs={"invite_code": self.invite.code})
        login_response = self.client.get(
            reverse("email_login_code"),
            data={"email": new_email, "code": code.code, "goto": goto},
        )
        self.assertRedirects(login_response, goto, fetch_redirect_response=False)
        self.assertTrue(self.client.is_authorised())

        response = self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": new_email},
            follow=True,
        )
        redirect_urls = [url for url, _status in response.redirect_chain]
        self.assertNotIn(reverse("membership_expired"), redirect_urls)

        self.invite.refresh_from_db()
        self.assertIsNotNone(self.invite.used_at)
        new_user = User.objects.get(email=new_email)
        self.assertEqual(self.invite.invited_user, new_user)
        self.assertGreater(
            new_user.membership_expires_at,
            datetime.utcnow() + timedelta(days=360),
        )

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

    def test_activation_adds_days_on_top_of_remaining_membership(self):
        self.client.authorise()
        expires_before = User.objects.get(id=self.existing_victim.id).membership_expires_at

        self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": self.existing_victim.email},
        )

        self.existing_victim.refresh_from_db()
        self.assertAlmostEqual(
            self.existing_victim.membership_expires_at,
            expires_before + timedelta(days=366),
            delta=timedelta(minutes=1),
        )

    def test_expired_member_starts_new_membership_from_today(self):
        expired_user = User.objects.create(
            email="expired@test.com",
            membership_started_at=datetime.now() - timedelta(days=400),
            membership_expires_at=datetime.now() - timedelta(days=30),
            slug="expired",
            moderation_status=User.MODERATION_STATUS_APPROVED,
        )
        client = HelperClient(user=expired_user).authorise()

        response = client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": expired_user.email},
        )

        self.assertRedirects(
            response,
            expected_url=f"/user/{expired_user.slug}/",
            fetch_redirect_response=False,
        )

        # days spent in the past must not eat into the freshly bought year
        expired_user.refresh_from_db()
        self.assertAlmostEqual(
            expired_user.membership_expires_at,
            datetime.utcnow() + timedelta(days=366),
            delta=timedelta(minutes=1),
        )

    def test_same_user_cannot_activate_invite_twice(self):
        self.client.authorise()

        self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": self.existing_victim.email},
        )
        expires_after_first = User.objects.get(id=self.existing_victim.id).membership_expires_at

        response = self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": self.existing_victim.email},
        )

        self.assertContains(response, "уже использован", status_code=200)

        self.existing_victim.refresh_from_db()
        self.assertEqual(self.existing_victim.membership_expires_at, expires_after_first)

    def test_used_invite_cannot_be_activated_by_another_user(self):
        self.client.authorise()
        self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": self.existing_victim.email},
        )

        latecomer = User.objects.create(
            email="latecomer@test.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            slug="latecomer",
            moderation_status=User.MODERATION_STATUS_APPROVED,
        )
        expires_before = User.objects.get(id=latecomer.id).membership_expires_at

        response = HelperClient(user=latecomer).authorise().post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": latecomer.email},
        )

        self.assertContains(response, "уже использован", status_code=200)

        latecomer.refresh_from_db()
        self.assertEqual(latecomer.membership_expires_at, expires_before)

        self.invite.refresh_from_db()
        self.assertEqual(self.invite.invited_user, self.existing_victim)

    def test_expired_invite_cannot_be_activated(self):
        Invite.objects.filter(id=self.invite.id).update(
            created_at=datetime.utcnow() - timedelta(days=INVITE_EXPIRATION_DAYS + 1)
        )
        self.client.authorise()
        expires_before = User.objects.get(id=self.existing_victim.id).membership_expires_at

        response = self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": self.existing_victim.email},
        )

        self.assertContains(response, "Этот инвайт истек", status_code=200)

        self.invite.refresh_from_db()
        self.assertIsNone(self.invite.used_at)

        self.existing_victim.refresh_from_db()
        self.assertEqual(self.existing_victim.membership_expires_at, expires_before)

    def test_anonymous_submitting_same_new_email_twice_creates_one_user(self):
        new_email = "twice@test.com"

        for _ in range(2):
            response = self.client.post(
                reverse("activate_invite", args=[self.invite.code]),
                data={"email": new_email},
            )
            self.assertContains(response, "Вам отправлен код!", status_code=200)

        self.assertEqual(User.objects.filter(email=new_email).count(), 1)

        self.invite.refresh_from_db()
        self.assertIsNone(self.invite.used_at)

    def test_anonymous_can_switch_to_another_email_before_activating(self):
        first_email = "first@test.com"
        second_email = "second@test.com"

        self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": first_email},
        )
        response = self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": second_email},
        )

        self.assertContains(response, second_email, status_code=200)
        self.assertIsNotNone(Code.objects.filter(recipient=first_email).first())
        self.assertIsNotNone(Code.objects.filter(recipient=second_email).first())

        self.invite.refresh_from_db()
        self.assertIsNone(self.invite.used_at)

    def test_email_is_normalized_before_activation(self):
        self.client.authorise()

        response = self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": f"  {self.existing_victim.email.upper()} "},
        )

        self.assertRedirects(
            response,
            expected_url=f"/user/{self.existing_victim.slug}/",
            fetch_redirect_response=False,
        )

        self.invite.refresh_from_db()
        self.assertEqual(self.invite.invited_user, self.existing_victim)

    def test_moderator_sees_who_used_the_invite(self):
        self.client.authorise()
        self.client.post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": self.existing_victim.email},
        )

        moderator = User.objects.create(
            email="invite_moderator@test.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=365),
            slug="invite_moderator",
            roles=[User.ROLE_MODERATOR],
            moderation_status=User.MODERATION_STATUS_APPROVED,
        )

        response = HelperClient(user=moderator).authorise().post(
            reverse("activate_invite", args=[self.invite.code]),
            data={"email": moderator.email},
        )

        self.assertContains(response, "Включен режим модератора", status_code=200)
        self.assertContains(response, self.existing_victim.slug)
