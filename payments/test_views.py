from datetime import datetime, timedelta
from collections import namedtuple
import os
import uuid

import django
from django.urls import reverse
from django.test import TestCase
import json
import time
import yaml
from unittest import skip
from unittest.mock import patch

from stripe.webhook import WebhookSignature

import authn.models.session

django.setup()  # todo: how to run tests from PyCharm without this workaround?

from payments.models import Payment
from payments.products import PRODUCTS
from debug.helpers import HelperClient
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


@patch('payments.views.stripe.stripe')
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
        self.assertAlmostEquals(created_user.membership_expires_at, datetime.utcnow(), delta=timedelta(seconds=5))
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

    def setUp(self):
        self.client = HelperClient()

        self.existed_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            slug="ujlbu4"
        )

    @staticmethod
    def read_json_event(event_file_name):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, f'./_stubs/{event_file_name}.json')
        with open(file_path, 'r') as f:
            json_event = yaml.safe_load(f.read())

        return json_event

    def test_event_checkout_session_completed_positive(self):
        # links:
        #   https://stripe.com/docs/webhooks/signatures
        #   https://stripe.com/docs/api/events/object

        # given
        product = PRODUCTS["club1"]
        opened_payment: Payment = Payment.create(reference=f"random-reference-{uuid.uuid4()}",
                                                 user=self.existed_user,
                                                 product=product)

        strip_secret = "stripe_secret"
        with self.settings(STRIPE_WEBHOOK_SECRET=strip_secret):
            json_event = self.read_json_event('checkout.session.completed')
            json_event['data']['object']['id'] = opened_payment.reference

            timestamp = int(time.time())
            signed_payload = f"{timestamp}.{json.dumps(json_event)}"
            computed_signature = WebhookSignature._compute_signature(signed_payload, strip_secret)

            # when
            header = {'HTTP_STRIPE_SIGNATURE': f't={timestamp},v1={computed_signature}'}
            response = self.client.post(reverse("stripe_webhook"), data=json_event,
                                        content_type='application/json', **header)

            # then
            self.assertEqual(response.status_code, 200)
            # subscription prolongated
            user = User.objects.get(id=self.existed_user.id)
            self.assertAlmostEquals(user.membership_expires_at,
                                    self.existed_user.membership_expires_at + product['data']['timedelta'],
                                    delta=timedelta(seconds=10))

    @skip("do we need throw error in case payment not found?")
    def test_event_checkout_session_completed_negative_payment_not_found(self):
        # given
        strip_secret = "stripe_secret"
        with self.settings(STRIPE_WEBHOOK_SECRET=strip_secret):
            json_event = self.read_json_event('checkout.session.completed')
            json_event['data']['object']['id'] = "some-payment-reference-not-existed"  # not existed payment reference

            timestamp = int(time.time())
            signed_payload = f"{timestamp}.{json.dumps(json_event)}"
            computed_signature = WebhookSignature._compute_signature(signed_payload, strip_secret)

            # when
            header = {'HTTP_STRIPE_SIGNATURE': f't={timestamp},v1={computed_signature}'}
            response = self.client.post(reverse("stripe_webhook"), data=json_event,
                                        content_type='application/json', **header)

            # then
            self.assertEqual(response.status_code, 409)  # conflict due to payment not found (let it try latter)
            # subscription expiration not prolongated
            user = User.objects.get(id=self.existed_user.id)
            self.assertEqual(user.membership_expires_at, self.existed_user.membership_expires_at)

    def test_event_invoice_paid_with_billing_reason_subscription_create_positive(self):
        # links:
        #   https://stripe.com/docs/webhooks/signatures
        #   https://stripe.com/docs/api/events/object

        # given
        strip_secret = "stripe_secret"
        with self.settings(STRIPE_WEBHOOK_SECRET=strip_secret):
            json_event = self.read_json_event('invoice.paid')
            json_event['data']['object']['id'] = f'payment-id-{uuid.uuid4()}'
            json_event['data']['object']['billing_reason'] = "subscription_create"

            timestamp = int(time.time())
            signed_payload = f"{timestamp}.{json.dumps(json_event)}"
            computed_signature = WebhookSignature._compute_signature(signed_payload, strip_secret)

            # when
            header = {'HTTP_STRIPE_SIGNATURE': f't={timestamp},v1={computed_signature}'}
            response = self.client.post(reverse("stripe_webhook"), data=json_event,
                                        content_type='application/json', **header)

            # then
            self.assertEqual(response.status_code, 200)
            # subscription not prolonging, cause it assumes it has already done in `checkout.session.completed` event
            user = User.objects.get(id=self.existed_user.id)
            self.assertEqual(user.membership_expires_at, self.existed_user.membership_expires_at)

    def test_event_invoice_paid_with_billing_reason_subscription_cycle_positive(self):
        # given
        strip_secret = "stripe_secret"
        with self.settings(STRIPE_WEBHOOK_SECRET=strip_secret):
            self.existed_user.stripe_id = f'stripe-id-{uuid.uuid4()}'
            self.existed_user.save()

            json_event = self.read_json_event('invoice.paid')
            json_event['data']['object']['id'] = f'payment-id-{uuid.uuid4()}'
            json_event['data']['object']['billing_reason'] = "subscription_cycle"
            json_event['data']['object']['customer'] = self.existed_user.stripe_id
            product = PRODUCTS['club1_recurrent_yearly']
            json_event['data']['object']['lines']["data"][0]["plan"]["id"] = product['stripe_id']

            timestamp = int(time.time())
            signed_payload = f"{timestamp}.{json.dumps(json_event)}"
            computed_signature = WebhookSignature._compute_signature(signed_payload, strip_secret)

            # when
            header = {'HTTP_STRIPE_SIGNATURE': f't={timestamp},v1={computed_signature}'}
            response = self.client.post(reverse("stripe_webhook"), data=json_event,
                                        content_type='application/json', **header)

            # then
            # subscription prolonged
            self.assertEqual(response.status_code, 200)
            # subscription prolonged
            user = User.objects.get(id=self.existed_user.id)
            self.assertAlmostEquals(user.membership_expires_at,
                                    self.existed_user.membership_expires_at + product['data']['timedelta'],
                                    delta=timedelta(seconds=10))

    @skip("do we need throw error in case payment not found?")
    def test_event_invoice_paid_negative_user_not_found(self):
        # given
        strip_secret = "stripe_secret"
        with self.settings(STRIPE_WEBHOOK_SECRET=strip_secret):
            strip_secret = "stripe_secret"
            with self.settings(STRIPE_WEBHOOK_SECRET=strip_secret):
                self.existed_user.stripe_id = f'stripe-id-{uuid.uuid4()}'
                self.existed_user.save()

                json_event = self.read_json_event('invoice.paid')
                json_event['data']['object']['id'] = f'payment-id-{uuid.uuid4()}'
                json_event['data']['object']['billing_reason'] = "subscription_cycle"
                json_event['data']['object']['customer'] = "not-existed-user"

                timestamp = int(time.time())
                signed_payload = f"{timestamp}.{json.dumps(json_event)}"
                computed_signature = WebhookSignature._compute_signature(signed_payload, strip_secret)

                # when
                header = {'HTTP_STRIPE_SIGNATURE': f't={timestamp},v1={computed_signature}'}
                response = self.client.post(reverse("stripe_webhook"), data=json_event,
                                            content_type='application/json', **header)

                # then
                self.assertEqual(response.status_code, 409)  # conflict due to payment not found (let it try latter)
                # subscription expiration not prolonged
                user = User.objects.get(id=self.existed_user.id)
                self.assertEqual(user.membership_expires_at, self.existed_user.membership_expires_at)

    def test_event_customer_updated_positive(self):
        strip_secret = "stripe_secret"
        with self.settings(STRIPE_WEBHOOK_SECRET=strip_secret):
            self.assertEqual(self.existed_user.stripe_id, None)

            json_event = self.read_json_event('customer.updated')
            json_event['data']['object']['email'] = self.existed_user.email

            timestamp = int(time.time())
            signed_payload = f"{timestamp}.{json.dumps(json_event)}"
            computed_signature = WebhookSignature._compute_signature(signed_payload, strip_secret)

            # when
            header = {'HTTP_STRIPE_SIGNATURE': f't={timestamp},v1={computed_signature}'}
            response = self.client.post(reverse("stripe_webhook"), data=json_event,
                                        content_type='application/json', **header)

            # then
            self.assertEqual(response.status_code, 200)
            # subscription not prolonging, cause it assumes it has already done in `checkout.session.completed` event
            user = User.objects.get(id=self.existed_user.id)
            self.assertEqual(user.stripe_id, json_event['data']['object']['id'])
            self.assertEqual(user.membership_expires_at, self.existed_user.membership_expires_at)

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
