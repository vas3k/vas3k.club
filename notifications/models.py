from uuid import uuid4

from django.db import models

from users.models.user import User


class WebhookEvent(models.Model):
    TYPE_EMAIL_BOUNCE = "email_bounce"
    TYPE_EMAIL_COMPLAINT = "email_complaint"
    TYPES = [
        (TYPE_EMAIL_BOUNCE, TYPE_EMAIL_BOUNCE),
        (TYPE_EMAIL_COMPLAINT, TYPE_EMAIL_COMPLAINT),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    type = models.CharField(max_length=32, choices=TYPES, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    recipient = models.CharField(max_length=128, null=True)
    data = models.JSONField(default=dict)

    class Meta:
        db_table = "webhook_events"

    @classmethod
    def register_event(cls, type, recipient, data):
        return WebhookEvent.objects.create(
            type=type,
            recipient=recipient,
            data=data,
        )
