import logging
from datetime import timedelta, datetime

import stripe
from django.db import transaction

from club.exceptions import BadRequest, InsufficientFunds
from users.models.user import User

log = logging.getLogger(__name__)


def parse_stripe_webhook_event(request, webhook_secret):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not payload or not sig_header:
        raise BadRequest(code=400, message="[invalid payload]")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise BadRequest(code=400, message="[invalid payload]")
    except stripe.error.SignatureVerificationError:
        raise BadRequest(code=400, message="[invalid signature]")

    return event


def cancel_all_stripe_subscriptions(stripe_id: str) -> bool:
    if not stripe_id:
        return False

    stripe_subscriptions = stripe.Subscription.list(customer=stripe_id, limit=100)
    for subscription in stripe_subscriptions["data"]:
        try:
            stripe.Subscription.delete(subscription["id"])
        except Exception:
            log.exception("Stripe subscription cancellation error")

    return True


def gift_membership_days(days, from_user, to_user, deduct_from_original_user=True):
    if days <= 0:
        raise BadRequest(message="Количество дней должно быть больше 0")

    amount = timedelta(days=days)

    if deduct_from_original_user and from_user.membership_expires_at - amount <= datetime.utcnow():
        raise InsufficientFunds()

    with transaction.atomic():
        if to_user.membership_expires_at <= datetime.utcnow():
            to_user.membership_expires_at = datetime.utcnow()
        to_user.membership_expires_at += amount
        to_user.membership_platform_type = User.MEMBERSHIP_PLATFORM_DIRECT
        to_user.save()

        if deduct_from_original_user:
            from_user.membership_expires_at -= amount
            from_user.save()

    return to_user.membership_expires_at
