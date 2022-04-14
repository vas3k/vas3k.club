import json
from uuid import uuid4

from django.db import models

from payments.exceptions import PaymentNotFound, PaymentAlreadyFinalized
from users.models.user import User


class Payment(models.Model):
    STATUS_STARTED = "started"
    STATUS_FAILED = "failed"
    STATUS_SUCCESS = "success"
    STATUSES = [
        (STATUS_STARTED, STATUS_STARTED),
        (STATUS_FAILED, STATUS_FAILED),
        (STATUS_SUCCESS, STATUS_SUCCESS),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    reference = models.CharField(max_length=256, db_index=True)
    user = models.ForeignKey(User, related_name="payments", null=True, on_delete=models.SET_NULL, db_index=True)
    product_code = models.CharField(max_length=64)

    created_at = models.DateTimeField(auto_now_add=True)

    amount = models.FloatField(default=0.0)
    status = models.CharField(choices=STATUSES, default=STATUS_STARTED, max_length=32)
    data = models.TextField(null=True)

    class Meta:
        db_table = "payments"

    @classmethod
    def create(cls, reference: str, user: User, product: dict, data: dict = None, status: str = STATUS_STARTED):
        return Payment.objects.create(
            reference=reference,
            user=user,
            product_code=product["code"],
            amount=product.get("amount") or 0.0,
            status=status,
            data=json.dumps(data),
        )

    @classmethod
    def get(cls, reference):
        return Payment.objects.filter(reference=reference).first()

    @classmethod
    def finish(cls, reference, status=STATUS_SUCCESS, data=None):
        payment = Payment.get(reference)
        if not payment:
            raise PaymentNotFound()

        if payment.status != cls.STATUS_STARTED and status == cls.STATUS_SUCCESS:
            raise PaymentAlreadyFinalized()

        payment.status = status
        if data:
            payment.data = json.dumps(data)
        payment.save()

        return payment

    @classmethod
    def for_user(cls, user):
        return Payment.objects.filter(user=user)

    def invited_user_email(self):
        # this is hacky, need to use a proper JSON field here
        if self.data:
            try:
                payment_data = json.loads(self.data)
                return payment_data.get("metadata", {}).get("invite") or payment_data.get("invite")
            except (KeyError, AttributeError):
                return None
        return None
