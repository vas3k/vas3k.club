import time
from uuid import uuid4

from django.db import models

from users.models.user import User


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    reference = models.CharField(max_length=256)
    user = models.ForeignKey(User, related_name="payments", null=True, on_delete=models.SET_NULL)
    product_code = models.CharField(max_length=64)

    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=32)

    class Meta:
        db_table = "payments"

    @classmethod
    def start(cls, user, product_code):
        reference = f"{user.slug}_{product_code}_{int(time.time())}"
        return Payment.objects.create(
            reference=reference,
            user=user,
            product_code=product_code,
        )

    @classmethod
    def get(cls, reference):
        return Payment.objects.filter(reference=reference).first()

    @classmethod
    def finish(cls, reference, status="success"):
        payment = Payment.get(reference)
        if payment:
            payment.status = status
            payment.save()
        return payment
