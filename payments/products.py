from datetime import datetime, timedelta

from users.models.user import User


def club_subscription_activator(product, payment, user):
    now = datetime.utcnow()
    if user.membership_expires_at < now:
        user.membership_expires_at = now  # ignore days in the past

    user.membership_expires_at += product["data"]["timedelta"]
    user.membership_platform_type = User.MEMBERSHIP_PLATFORM_DIRECT
    user.membership_platform_data = {"reference": payment.reference}
    user.save()

    return True


PRODUCTS = {
    "club1": {
        "code": "club1",
        "stripe_id": "price_1H5byfKgJMaF2rHtJHeirP4V",
        "description": "Членство в Клубе на год",
        "amount": 15,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365),
        },
    },
    "club3": {
        "code": "club3",
        "stripe_id": "price_1H5c1sKgJMaF2rHtEQ1Jl7Pt",
        "description": "Членство в Клубе на 3 года",
        "amount": 40,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 3),
        },
    },
    "club50": {
        "code": "club50",
        "stripe_id": "price_1H5c3JKgJMaF2rHtPiIED05T",
        "description": "Членство в Клубе на 50 лет",
        "amount": 150,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 50),
        },
    },
}
