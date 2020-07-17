import json
from uuid import uuid4

from django.db import models

from users.models.user import User


class Payment(models.Model):
    PAYMENT_STATUS_STARTED = "started"
    PAYMENT_STATUS_FAILED = "failed"
    PAYMENT_STATUS_SUCCESS = "success"
    PAYMENT_STATUSES = [
        (PAYMENT_STATUS_STARTED, PAYMENT_STATUS_STARTED),
        (PAYMENT_STATUS_FAILED, PAYMENT_STATUS_FAILED),
        (PAYMENT_STATUS_SUCCESS, PAYMENT_STATUS_SUCCESS),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    reference = models.CharField(max_length=256)
    user = models.ForeignKey(User, related_name="payments", null=True, on_delete=models.SET_NULL)
    product_code = models.CharField(max_length=64)

    created_at = models.DateTimeField(auto_now_add=True)

    amount = models.FloatField(default=0.0)
    status = models.CharField(choices=PAYMENT_STATUSES, default=PAYMENT_STATUS_STARTED, max_length=32)
    data = models.TextField(null=True)

    class Meta:
        db_table = "payments"

    @classmethod
    def start(cls, reference, user, product):
        return Payment.objects.create(
            reference=reference,
            user=user,
            product_code=product["code"],
            amount=product.get("amount") or 0.0,
        )

    @classmethod
    def get(cls, reference):
        return Payment.objects.filter(reference=reference).first()

    @classmethod
    def finish(cls, reference, status=PAYMENT_STATUS_SUCCESS, data=None):
        payment = Payment.get(reference)
        if payment:
            payment.status = status
            payment.data = json.dumps(data)
            payment.save()
        return payment
