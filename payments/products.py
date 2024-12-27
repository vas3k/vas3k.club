import logging
from datetime import datetime, timedelta

from django.conf import settings
from django_q.tasks import async_task

from invites.models import Invite
from notifications.email.invites import send_invite_purchase_confirmation
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
    invite = Invite.objects.create(
        user=user,
        payment=payment,
    )

    # send notification to author
    async_task(send_invite_purchase_confirmation, user, invite)

    return True


PRODUCTS = {
    "club1": {
        "code": "club1",
        "stripe_id": "price_1QZtkpKgJMaF2rHtKAVKNJoB" if not IS_TEST_STRIPE else "price_1H5cChKgJMaF2rHtugvlcjKR",
        "coinbase_id": "e69b2ee9-d363-42c1-9f5d-64366922121f",
        "description": "Год членства в Клубе",
        "amount": 25,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=366),
        },
    },
    "club1_recurrent_yearly": {
        "code": "club1_recurrent_yearly",
        "stripe_id": "price_1QZtlFKgJMaF2rHtnQZEkqTD" if not IS_TEST_STRIPE else "price_1H74BCKgJMaF2rHtRhUtbn3C",
        "coinbase_id": "e69b2ee9-d363-42c1-9f5d-64366922121f",
        "description": "Год членства в Клубе (автопополнение каждый год)",
        "amount": 25,
        "recurrent": "yearly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=366),
        },
    },
    "legacy_club1_recurrent_yearly_02": {
        "code": "club1_recurrent_yearly",
        "stripe_id": "price_1M5rx4KgJMaF2rHtR2i0Dfo8",
        "coinbase_id": "e69b2ee9-d363-42c1-9f5d-64366922121f",
        "description": "Год членства в Клубе (автопополнение каждый год)",
        "amount": 20,
        "recurrent": "yearly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=366),
        },
    },
    "legacy_club1_recurrent_yearly_01": {
        "code": "club1_recurrent_yearly",
        "stripe_id": "price_1H73kbKgJMaF2rHtTS3clmtv",
        "coinbase_id": "e69b2ee9-d363-42c1-9f5d-64366922121f",
        "description": "Год членства в Клубе  (автопродление, легаси)",
        "amount": 15,
        "recurrent": "yearly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=366),
        },
    },
    "club3": {
        "code": "club3",
        "stripe_id": "price_1QZtmZKgJMaF2rHtMfWJ5QFs" if not IS_TEST_STRIPE else "price_1H5cChKgJMaF2rHtugvlcjKR",
        "coinbase_id": "84c507f9-0a21-471f-8d10-acf0a154db0d",
        "description": "Членство в Клубе на 3 года",
        "amount": 55,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 3),
        },
    },
    "club3_recurrent_yearly": {
        "code": "club3_recurrent_yearly",
        "stripe_id": "price_1QZtmqKgJMaF2rHtjP9aT80d" if not IS_TEST_STRIPE else "price_1H74BCKgJMaF2rHtRhUtbn3C",
        "coinbase_id": "84c507f9-0a21-471f-8d10-acf0a154db0d",
        "description": "+3 года членства в Клубе (автопродление)",
        "amount": 55,
        "recurrent": "yearly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 3),
        },
    },
    "club50": {
        "code": "club50",
        "stripe_id": "price_1QZto2KgJMaF2rHtDJsQke42" if not IS_TEST_STRIPE else "price_1H5cChKgJMaF2rHtugvlcjKR",
        "coinbase_id": "ff0df23f-06d8-473f-9ad8-74039a62aeb1",
        "description": "Членство в Клубе на 50 лет",
        "amount": 350,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 50),
        },
    },
    "club50_recurrent_yearly": {
        "code": "club50_recurrent_yearly",
        "stripe_id": "price_1QZu3WKgJMaF2rHt1jtw3mEb" if not IS_TEST_STRIPE else "price_1H74BCKgJMaF2rHtRhUtbn3C",
        "coinbase_id": "ff0df23f-06d8-473f-9ad8-74039a62aeb1",
        "description": "Членство в Клубе на 50 лет (автопополнение каждый год)",
        "amount": 250,
        "recurrent": "yearly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 50),
        },
    },
    "legacy_club50_recurrent_yearly_02": {
        "code": "club50_recurrent_yearly",
        "stripe_id": "price_1OmKAFKgJMaF2rHtxoB6YQB6" if not IS_TEST_STRIPE else "price_1H74BCKgJMaF2rHtRhUtbn3C",
        "coinbase_id": "ff0df23f-06d8-473f-9ad8-74039a62aeb1",
        "description": "Членство в Клубе на 50 лет (автопополнение каждый год)",
        "amount": 250,
        "recurrent": "yearly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 50),
        },
    },
    "club1_invite": {
        "code": "club1_invite",
        "stripe_id": "price_1QZtjxKgJMaF2rHt8e3VWP0V" if not IS_TEST_STRIPE else "price_1IX9QuKgJMaF2rHtJnrSs0Ud",
        "coinbase_id": None,
        "description": "Инвайт в Клуб",
        "amount": 25,
        "recurrent": False,
        "activator": club_invite_activator,
        "data": {
            "timedelta": timedelta(days=366),
        },
    },
}


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
