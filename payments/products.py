from datetime import datetime, timedelta

from django.conf import settings

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
        "amount": 15,
        "description": "Членство в Клубе на год",
        "return_url": f"{settings.APP_HOST}/monies/done/",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365),
        },
    },
    "club3": {
        "code": "club3",
        "amount": 40,
        "description": "Членство в Клубе на 3 года",
        "return_url": f"{settings.APP_HOST}/monies/done/",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 3),
        },
    },
    "club50": {
        "code": "club50",
        "amount": 150,
        "description": "Членство в Клубе на 50 лет",
        "return_url": f"{settings.APP_HOST}/monies/done/",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 50),
        },
    },
}
