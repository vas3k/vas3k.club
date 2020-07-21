from datetime import datetime, timedelta

from django.conf import settings

from users.models.user import User


IS_TEST_STRIPE = settings.STRIPE_API_KEY.startswith("sk_test")


def club_subscription_activator(product, payment, user):
    now = datetime.utcnow()
    if user.membership_expires_at < now:
        user.membership_expires_at = now  # ignore days in the past

    user.membership_expires_at += product["data"]["timedelta"]
    user.membership_platform_type = User.MEMBERSHIP_PLATFORM_DIRECT
    user.membership_platform_data = {
        "reference": payment.reference,
        "recurrent": product.get("recurrent"),
    }
    user.save()

    return True


PRODUCTS = {
    "club1": {
        "code": "club1",
        "stripe_id": "price_1H5byfKgJMaF2rHtJHeirP4V" if not IS_TEST_STRIPE else "price_1H5cChKgJMaF2rHtugvlcjKR",
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
        "description": "Членство в Клубе на 50 лет (автопополнение каждый месяц)",
        "amount": 150,
        "recurrent": "monthly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 50),
        },
    },
}


def find_by_price_id(price_id):
    for product in PRODUCTS.values():
        if product["stripe_id"] == price_id:
            return product
    return None
