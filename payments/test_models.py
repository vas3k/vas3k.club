from datetime import datetime, timedelta
import uuid
import django
from django.conf import settings
from django.test import TestCase

django.setup()  # todo: how to run tests from PyCharm without this workaround?

from payments.models import Payment
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
            Payment.objects.filter(pk=payment.id).exists,
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

    def test_finis_payment_not_existed_payment(self):
        result = Payment.finish(reference="wrong-not-existed-reference",
                                status=Payment.STATUS_FAILED,
                                data={"some": "data"})
        self.assertIsNone(result)

