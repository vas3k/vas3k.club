from datetime import datetime, timedelta
import uuid
import django
from django.conf import settings
from django.test import TestCase

django.setup()  # todo: how to run tests from PyCharm without this workaround?

from payments.models import Payment
from payments.exceptions import PaymentNotFound
from payments import products
from payments.products import PRODUCTS
from users.models.user import User


class TestPaymentModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up data for the whole TestCase
        cls.existed_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
        )

        cls.existed_payment: Payment = Payment.create(reference=f"random-reference-{uuid.uuid4()}",
                                                      user=cls.existed_user,
                                                      product=PRODUCTS["club1"],
                                                      data={"fake-prop": 1},
                                                      status=Payment.STATUS_STARTED)

    def test_create_payment_positive(self):
        # when
        payment: Payment = Payment.create(reference=f"random-reference-{uuid.uuid4()}",
                                          user=self.existed_user,
                                          product=PRODUCTS["club1"],
                                          data={"fake-prop": 1},
                                          status=Payment.STATUS_STARTED)

        # then
        self.assertIsNotNone(payment)
        self.assertIsNotNone(payment.id)
        self.assertTrue(
            Payment.objects.filter(pk=payment.id).exists(),
            "The only payment I expect is here, persisted, and correct."
        )

    def test_get_payment_by_reference_positive(self):
        # when
        payment: Payment = Payment.get(reference=self.existed_payment.reference)

        # then
        self.assertIsNotNone(payment)
        self.assertEqual(payment.id, self.existed_payment.id)

    def test_get_payment_by_reference_not_existed_reference(self):
        payment: Payment = Payment.get(reference="wrong-not-existed-reference")
        self.assertIsNone(payment)

    def test_finish_payment_positive(self):
        result: Payment = Payment.finish(reference=self.existed_payment.reference,
                                         status=Payment.STATUS_SUCCESS,
                                         data={"some": "data"})

        self.assertIsNotNone(result)
        # check it persistent
        payment = Payment.get(reference=result.reference)
        self.assertIsNotNone(payment)
        self.assertEqual(payment.id, self.existed_payment.id)
        self.assertEqual(payment.status, Payment.STATUS_SUCCESS)
        self.assertEqual(payment.data, '{"some": "data"}')

    def test_finish_non_existent_payment_exception(self):
        with self.assertRaises(PaymentNotFound):
            result = Payment.finish(reference="wrong-not-existed-reference",
                                    status=Payment.STATUS_FAILED,
                                    data={"some": "data"})


class TestProducts(TestCase):

    def test_club_subscription_activator_positive_membership_expires_in_future(self):
        # given
        future_membership_expiration = datetime.utcnow() + timedelta(days=5)
        existed_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.utcnow() - timedelta(days=5),
            membership_expires_at=future_membership_expiration,
        )
        new_payment: Payment = Payment.create(reference=f"random-reference-{uuid.uuid4()}",
                                              user=existed_user,
                                              product=PRODUCTS["club1"])

        # when
        result = products.club_subscription_activator(product=PRODUCTS["club1_recurrent_yearly"],
                                                      payment=new_payment,
                                                      user=existed_user)

        # then
        self.assertTrue(result)

        user = User.objects.get(id=existed_user.id)
        self.assertAlmostEquals(user.membership_expires_at, future_membership_expiration + timedelta(days=366),
                                delta=timedelta(seconds=10))
        self.assertEqual(user.membership_platform_type, User.MEMBERSHIP_PLATFORM_DIRECT)
        self.assertEqual(user.membership_platform_data, {"reference": new_payment.reference,
                                                         "recurrent": "yearly"})

    def test_club_subscription_activator_positive_membership_expires_in_past(self):
        # given
        membership_expiration_in_past = datetime.utcnow() - timedelta(days=5)
        existed_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.utcnow() - timedelta(days=10),
            membership_expires_at=membership_expiration_in_past,
        )
        new_payment: Payment = Payment.create(reference=f"random-reference-{uuid.uuid4()}",
                                              user=existed_user,
                                              product=PRODUCTS["club1"])

        # when
        result = products.club_subscription_activator(product=PRODUCTS["club1_recurrent_yearly"],
                                                      payment=new_payment,
                                                      user=existed_user)

        # then
        self.assertTrue(result)

        user = User.objects.get(id=existed_user.id)
        self.assertAlmostEquals(user.membership_expires_at, datetime.utcnow() + timedelta(days=366),
                                delta=timedelta(seconds=10))
        self.assertEqual(user.membership_platform_type, User.MEMBERSHIP_PLATFORM_DIRECT)
        self.assertEqual(user.membership_platform_data, {"reference": new_payment.reference,
                                                         "recurrent": "yearly"})

    def test_find_by_price_id_positive(self):
        product = PRODUCTS['club1_recurrent_yearly']
        price_id = product['stripe_id']
        result = products.find_by_stripe_id(price_id=price_id)

        self.assertIsNotNone(result)
        self.assertEqual(result, product)

    def test_find_by_price_id_not_existed(self):
        result = products.find_by_stripe_id(price_id="not-existed-price-id")

        self.assertIsNone(result)
