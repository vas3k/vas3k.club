import hmac
import json

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST

from notifications.models import WebhookEvent


@require_POST
def webhook_event(request, event_type):
    secret = request.GET.get("secret", "")
    if not secret or not _is_valid_secret(secret):
        return HttpResponseForbidden("Forbidden")

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)

    handler = WEBHOOK_HANDLERS.get(event_type) or WEBHOOK_HANDLERS["default"]
    handler(
        event_type=event_type,
        data=data,
    )
    return HttpResponse("OK")


def _is_valid_secret(secret):
    return any(
        hmac.compare_digest(secret, expected)
        for expected in settings.WEBHOOK_SECRETS
    )


def default_webhook_handler(event_type, data):
    return WebhookEvent.register_event(
        type=event_type,
        recipient=None,
        data=data
    )


WEBHOOK_HANDLERS = {
    WebhookEvent.TYPE_EMAIL_BOUNCE: default_webhook_handler,
    WebhookEvent.TYPE_EMAIL_COMPLAINT: default_webhook_handler,
    "default": default_webhook_handler,
}
