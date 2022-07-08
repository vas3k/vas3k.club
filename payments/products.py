import logging
from datetime import datetime, timedelta

from django.conf import settings
from django_q.tasks import async_task

from notifications.email.invites import send_invited_email, send_invite_confirmation, send_invite_renewed_email
from notifications.email.users import send_registration_email, send_renewal_email
from users.models.user import User

log = logging.getLogger(__name__)

IS_TEST_STRIPE = settings.STRIPE_API_KEY.startswith("sk_test")


def club_subscription_activator(product, payment, user):
    now = datetime.utcnow()
    if user.membership_expires_at < now:
        user.membership_expires_at = now  # ignore days in the past

    user.membership_expires_at += product["data"]["timedelta"]

    # force patreon migration
    if user.membership_platform_type == User.MEMBERSHIP_PLATFORM_PATREON:
        user.membership_platform_type = User.MEMBERSHIP_PLATFORM_DIRECT

    user.membership_platform_data = {
        "reference": payment.reference,
        "recurrent": product.get("recurrent"),
    }
    user.save()

    # notify the user
    if user.moderation_status == User.MODERATION_STATUS_INTRO:
        async_task(send_registration_email, user)
    else:
        async_task(send_renewal_email, user)

    return True


def club_invite_activator(product, payment, user):
    friend_email = payment.invited_user_email()
    if not friend_email:
        log.error(f"Friend email not set in payment: {payment.id}")
        return club_subscription_activator(product, payment, user)

    friend = User.objects.filter(email=friend_email).first()
    if not friend:
        log.error(f"Friend not found: {friend_email}")
        return club_subscription_activator(product, payment, user)

    # notify invited user
    if friend.moderation_status == User.MODERATION_STATUS_INTRO:
        async_task(send_invited_email, user, friend)
    else:
        async_task(send_invite_renewed_email, user, friend)

    # send notification to author
    async_task(send_invite_confirmation, user, friend)

    return club_subscription_activator(product, payment, friend)


PRODUCTS = {
    "club1": {
        "code": "club1",
        "stripe_id": "price_1H5byfKgJMaF2rHtJHeirP4V" if not IS_TEST_STRIPE else "price_1H5cChKgJMaF2rHtugvlcjKR",
        "coinbase_id": "e69b2ee9-d363-42c1-9f5d-64366922121f",
        "description": "Год членства в Клубе",
        "amount": 15,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365),
        },
    },
    "club1_recurrent_yearly": {
        "code": "club1_recurrent_yearly",
        "stripe_id": "price_1H73kbKgJMaF2rHtTS3clmtv" if not IS_TEST_STRIPE else "price_1H74BCKgJMaF2rHtRhUtbn3C",
        "coinbase_id": "e69b2ee9-d363-42c1-9f5d-64366922121f",
        "description": "Год членства в Клубе (автопополнение каждый год)",
        "amount": 15,
        "recurrent": "yearly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365),
        },
    },
    "club1_recurrent_monthly": {
        "code": "club1_recurrent_monthly",
        "stripe_id": "price_1H73luKgJMaF2rHteHuMsvBE" if not IS_TEST_STRIPE else "price_1H74BCKgJMaF2rHtRhUtbn3C",
        "coinbase_id": "e69b2ee9-d363-42c1-9f5d-64366922121f",
        "description": "Год членства в Клубе (автопополнение каждый месяц)",
        "amount": 15,
        "recurrent": "monthly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365),
        },
    },
    "club3": {
        "code": "club3",
        "stripe_id": "price_1H5c1sKgJMaF2rHtEQ1Jl7Pt" if not IS_TEST_STRIPE else "price_1H5cChKgJMaF2rHtugvlcjKR",
        "coinbase_id": "84c507f9-0a21-471f-8d10-acf0a154db0d",
        "description": "Членство в Клубе на 3 года",
        "amount": 40,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 3),
        },
    },
    "club3_recurrent_yearly": {
        "code": "club3_recurrent_yearly",
        "stripe_id": "price_1H73n7KgJMaF2rHtZtU9dvJT" if not IS_TEST_STRIPE else "price_1H74BCKgJMaF2rHtRhUtbn3C",
        "coinbase_id": "84c507f9-0a21-471f-8d10-acf0a154db0d",
        "description": "+3 года членства в Клубе (автопополнение каждый год)",
        "amount": 40,
        "recurrent": "yearly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 3),
        },
    },
    "club3_recurrent_monthly": {
        "code": "club3_recurrent_monthly",
        "stripe_id": "price_1H73oXKgJMaF2rHtITGhACgO" if not IS_TEST_STRIPE else "price_1H74BCKgJMaF2rHtRhUtbn3C",
        "coinbase_id": "84c507f9-0a21-471f-8d10-acf0a154db0d",
        "description": "+3 года членства в Клубе (автопополнение каждый месяц)",
        "amount": 40,
        "recurrent": "monthly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 3),
        },
    },
    "club50": {
        "code": "club50",
        "stripe_id": "price_1H5c3JKgJMaF2rHtPiIED05T" if not IS_TEST_STRIPE else "price_1H5cChKgJMaF2rHtugvlcjKR",
        "coinbase_id": "ff0df23f-06d8-473f-9ad8-74039a62aeb1",
        "description": "Членство в Клубе на 50 лет",
        "amount": 150,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 50),
        },
    },
    "club50_recurrent_yearly": {
        "code": "club50_recurrent_yearly",
        "stripe_id": "price_1H73rBKgJMaF2rHtyaW1DGWM" if not IS_TEST_STRIPE else "price_1H74BCKgJMaF2rHtRhUtbn3C",
        "coinbase_id": "ff0df23f-06d8-473f-9ad8-74039a62aeb1",
        "description": "Членство в Клубе на 50 лет (автопополнение каждый год)",
        "amount": 150,
        "recurrent": "yearly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 50),
        },
    },
    "club50_recurrent_monthly": {
        "code": "club50_recurrent_monthly",
        "stripe_id": "price_1H73q7KgJMaF2rHtswNA3rha" if not IS_TEST_STRIPE else "price_1H74BCKgJMaF2rHtRhUtbn3C",
        "coinbase_id": "ff0df23f-06d8-473f-9ad8-74039a62aeb1",
        "description": "Членство в Клубе на 50 лет (автопополнение каждый месяц)",
        "amount": 150,
        "recurrent": "monthly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 50),
        },
    },
    "club1_invite": {
        "code": "club1_invite",
        "stripe_id": "price_1IXA3fKgJMaF2rHtq37jPrym" if not IS_TEST_STRIPE else "price_1IX9QuKgJMaF2rHtJnrSs0Ud",
        "coinbase_id": None,
        "description": "Пригласить друга в Клуб",
        "amount": 15,
        "recurrent": False,
        "activator": club_invite_activator,
        "data": {
            "timedelta": timedelta(days=365),
        },
    },
}

TAX_RATE_VAT = "txr_1I82AfKgJMaF2rHtoUStb1cL" if not IS_TEST_STRIPE else None


def find_by_stripe_id(price_id):
    for product in PRODUCTS.values():
        if product["stripe_id"] == price_id:
            return product
    log.error(f"Can't find the product: {price_id}")
    return None


def find_by_coinbase_id(coinbase_id):
    for product in PRODUCTS.values():
        if product["coinbase_id"] == coinbase_id:
            return product
    log.error(f"Can't find the product: {coinbase_id}")
    return None
