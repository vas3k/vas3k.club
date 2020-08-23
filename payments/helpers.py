import logging

import stripe

log = logging.getLogger(__name__)


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
