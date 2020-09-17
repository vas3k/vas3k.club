from datetime import datetime, timedelta
from collections import namedtuple
import uuid
import django
from django.urls import reverse
from django.conf import settings
from django.test import SimpleTestCase, TestCase
from unittest.mock import patch

django.setup()  # todo: how to run tests from PyCharm without this workaround?

from payments.models import Payment
from payments.products import PRODUCTS
from tests.helpers import HelperClient
from users.models.user import User


class TestMembershipExpired(TestCase):

    def test_membership_expires_future(self):
        # given
        new_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            slug="ujlbu4"
        )
        client = HelperClient(user=new_user)
        client.authorise()

        # when
        response = client.get(reverse('membership_expired'))
        self.assertRedirects(response=response, expected_url=f'/user/{new_user.slug}/',
                             fetch_redirect_response=False)

    def test_membership_already_expired(self):
        # given
        new_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.now() - timedelta(days=10),
            membership_expires_at=datetime.now() - timedelta(days=5),
            slug="ujlbu4"
        )
        client = HelperClient(user=new_user)
        client.authorise()

        # when
        response = client.get(reverse('membership_expired'))
        self.assertContains(response=response, text="Ваша клубная карта истекла", status_code=200)

    def test_user_unauthorized(self):
        # given
        client = HelperClient()
        self.assertFalse(client.is_authorised())

        # when
        response = client.get(reverse('membership_expired'))
        self.assertRedirects(response=response, expected_url=f'/', fetch_redirect_response=False)


class TestDoneView(TestCase):

    def setUp(self):
        self.client = HelperClient(user=None)

    def test_club_member(self):
        existed_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.utcnow() - timedelta(days=5),
            membership_expires_at=datetime.utcnow() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            slug="ujlbu4",
        )
        existed_payment: Payment = Payment.create(reference=f"random-reference-{uuid.uuid4()}",
                                                  user=existed_user,
                                                  product=PRODUCTS["club1"])

        response = self.client.get(reverse('done'), data={'reference': existed_payment.reference})
        self.assertContains(response=response, text="Ваша клубная карта продлена", status_code=200)

    def test_not_club_member(self):
        existed_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.utcnow() - timedelta(days=5),
            membership_expires_at=datetime.utcnow() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_INTRO,
            slug="ujlbu4",
        )
        existed_payment: Payment = Payment.create(reference=f"random-reference-{uuid.uuid4()}",
                                                  user=existed_user,
                                                  product=PRODUCTS["club1"])

        response = self.client.get(reverse('done'), data={'reference': existed_payment.reference})
        self.assertContains(response=response, text="Теперь у вас есть аккаунт в Клубе", status_code=200)

    def test_reference_not_found(self):
        response = self.client.get(reverse('done'), data={'reference': 'wrong-reference'})
        self.assertContains(response=response, text="Теперь у вас есть аккаунт в Клубе", status_code=200)


@patch('payments.views.stripe')
class TestPayView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.existed_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            slug="ujlbu4"
        )

    def setUp(self):
        self.client = HelperClient(user=self.existed_user)

    def test_positive_new_user(self, mocked_stripe):
        # given
        product_code = "club1"
        email = f"new-user-{uuid.uuid4()}@email.com"
        StripeSession = namedtuple('Session', "id")
        session = StripeSession(id=f"{uuid.uuid4()}")
        mocked_stripe.checkout.Session.create.return_value = session

        # when
        response = self.client.get(reverse("pay"),
                                   data={
                                       "product_code": product_code,
                                       # "is_recurrent": PRODUCTS[product_code]["recurrent"],
                                       "email": email
                                   })

        # check
        self.assertTrue(User.objects.filter(email=email).exists, )
        created_user: User = User.objects.get(email=email)
        self.assertEqual(created_user.email, email)
        self.assertEqual(created_user.membership_platform_type, User.MEMBERSHIP_PLATFORM_DIRECT)
        self.assertEqual(created_user.full_name, email.replace("@email.com", ""))
        self.assertAlmostEquals(created_user.membership_started_at, datetime.utcnow(), delta=timedelta(seconds=5))
        self.assertAlmostEquals(created_user.membership_expires_at, datetime.utcnow() + timedelta(days=1),
                                delta=timedelta(seconds=5))
        self.assertEqual(created_user.moderation_status, User.MODERATION_STATUS_INTRO)

        self.assertTrue(Payment.get(reference=session.id))
        self.assertContains(response=response, text="Платим 💰", status_code=200)

    def test_positive_existed_user(self):
        self.assertTrue()

    def test_negative_new_user_with_broken_email(self):
        self.assertTrue(False)

    def test_product_not_found(self):
        self.assertTrue(False)
