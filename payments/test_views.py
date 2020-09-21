from datetime import datetime, timedelta
from collections import namedtuple
import uuid
import django
from django.urls import reverse
from django.conf import settings
from django.test import SimpleTestCase, TestCase
import json
import time
from unittest.mock import patch

from stripe.webhook import WebhookSignature

django.setup()  # todo: how to run tests from PyCharm without this workaround?

from payments.models import Payment
from payments.products import PRODUCTS
from tests.helpers import HelperClient
from users.models.user import User


class TestMembershipExpiredView(TestCase):

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
        self.assertTrue(User.objects.filter(email=email).exists(), )
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

    def test_positive_existed_authorised_user(self, mocked_stripe):
        # given
        product_code = "club1"
        StripeSession = namedtuple('Session', "id")
        session = StripeSession(id=f"{uuid.uuid4()}")
        mocked_stripe.checkout.Session.create.return_value = session
        self.client.authorise()

        # when
        response = self.client.get(reverse("pay"),
                                   data={
                                       "product_code": product_code,
                                   })

        # check
        self.assertTrue(User.objects.filter(email=self.existed_user.email).exists(), )
        user_after: User = User.objects.get(email=self.existed_user.email)
        self.assertEqual(user_after.membership_platform_type, self.existed_user.membership_platform_type)
        self.assertEqual(user_after.full_name, self.existed_user.full_name)
        self.assertEqual(user_after.membership_started_at, self.existed_user.membership_started_at)
        self.assertAlmostEquals(user_after.membership_expires_at, self.existed_user.membership_expires_at)
        self.assertEqual(user_after.moderation_status, self.existed_user.moderation_status)

        self.assertTrue(Payment.get(reference=session.id))
        self.assertContains(response=response, text="Платим 💰", status_code=200)

    def test_negative_new_user_with_broken_email(self, mocked_stripe):
        # given
        product_code = "club1"
        broken_email = f"email-invalid"

        # when
        response = self.client.get(reverse("pay"),
                                   data={
                                       "product_code": product_code,
                                       "email": broken_email
                                   })

        # check
        self.assertFalse(User.objects.filter(email=broken_email).exists(), )
        self.assertContains(response=response, text="Плохой e-mail адрес", status_code=200)

    def test_product_not_found(self, mocked_stripe):
        product_code = "unexisted-product-code"

        # when
        response = self.client.get(reverse("pay"),
                                   data={
                                       "product_code": product_code,
                                   })

        # check
        self.assertContains(response=response, text="Не выбран пакет", status_code=200)


class TestStripeWebhookView(TestCase):

    def setup(self):
        self.client = HelperClient()

    def test_(self):
        # links:
        #   https://stripe.com/docs/webhooks/signatures
        #   https://stripe.com/docs/api/events/object

        strip_secret = "stripe_secret"
        with self.settings(STRIPE_WEBHOOK_SECRET=strip_secret):
            timestamp = int(time.time())
            signature = "6844409814d3258cc0d08cac7b942e3ee27c34b09efd105bd3b2e1111c15a16c"
            json_data = """{
  "id": "evt_1CiPtv2eZvKYlo2CcUZsDcO6",
  "object": "event",
  "api_version": "2018-05-21",
  "created": 1530291411,
  "data": {
    "object": {
      "id": "cs_test_J60UFbzAxRlESqK4V5JiREcXWxyO7JKWqYcBJ4M6lJ049EOGAwowNPUI",
      "object": "checkout.session",
      "amount_subtotal": 4000,
      "amount_total": 4000,
      "billing_address_collection": null,
      "cancel_url": "http://127.0.0.1:8000/join/",
      "client_reference_id": null,
      "currency": "eur",
      "customer": "cus_HggKhYyxiBopsO",
      "customer_email": "me+bewbew@vas3k.ru",
      "livemode": false,
      "locale": null,
      "metadata": {
      },
      "mode": "subscription",
      "payment_intent": null,
      "payment_method_types": [
        "card"
      ],
      "setup_intent": null,
      "shipping": null,
      "shipping_address_collection": null,
      "submit_type": null,
      "subscription": "sub_HggKyfpIktYmlt",
      "success_url": "http://127.0.0.1:8000/monies/done/?reference={CHECKOUT_SESSION_ID}",
      "total_details": {
        "amount_discount": 0,
        "amount_tax": 0
      }
    }
  },
  "livemode": false,
  "pending_webhooks": 0,
  "request": {
    "id": null,
    "idempotency_key": null
  },
  "type": "checkout.session.completed"
}
"""

            signed_payload = f"{timestamp}.{json.dumps(json.loads(json_data))}"
            computed_signature = WebhookSignature._compute_signature(signed_payload, strip_secret)

            header = {'HTTP_STRIPE_SIGNATURE': f't={timestamp},v1={computed_signature}'}
            response = self.client.post(reverse("stripe_webhook"), data=json.loads(json_data),
                                        content_type='application/json', **header)

        self.assertTrue(False)

    def test_negative_no_payload(self):
        header = {'HTTP_STRIPE_SIGNATURE': 'xxx'}
        response = self.client.post(reverse("stripe_webhook"), content_type='application/json', **header)

        self.assertEqual(response.status_code, 400)

    def test_negative_no_signature(self):
        response = self.client.post(reverse("stripe_webhook"), data={"xxx": 1}, content_type='application/json')

        self.assertEqual(response.status_code, 400)

    def test_negative_invalid_signature(self):
        header = {'HTTP_STRIPE_SIGNATURE': 'invalid-signature'}
        with self.settings(STRIPE_WEBHOOK_SECRET="stripe_secret"):
            response = self.client.post(reverse("stripe_webhook"), data={"xxx": 1}, content_type='application/json',
                                        **header)

            self.assertEqual(response.status_code, 400)
