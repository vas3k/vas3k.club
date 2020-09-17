from datetime import datetime, timedelta
import uuid
import django
from django.urls import reverse
from django.conf import settings
from django.test import SimpleTestCase, TestCase

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
