import logging
import uuid
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from yookassa import Configuration, Payment as YookassaPayment

from club.exceptions import BadRequest
from payments.exceptions import PaymentException
from payments.helpers import parse_yookassa_webhook_event
from payments.models import Payment
from payments.products import YOOKASSA_PRODUCTS
from users.models.user import User

log = logging.getLogger()

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_API_KEY

def rubles(request):
    now = datetime.utcnow()

    if not request.me:  # scenario 1: new user
        # parse email
        email = request.GET.get("email") or ""
        if email:
            email = email.lower().strip()

        if not email or "@" not in email:
            return render(request, "payments/rubles.html", {})

        user, _ = User.objects.get_or_create(
            email=email,
            defaults=dict(
                membership_platform_type=User.MEMBERSHIP_PLATFORM_DIRECT,
                full_name=email[:email.find("@")],
                membership_started_at=now,
                membership_expires_at=now,
                created_at=now,
                updated_at=now,
                moderation_status=User.MODERATION_STATUS_INTRO,
            ),
        )
    else:  # scenario 2: account renewal or invite purchase
        user = request.me

    product = YOOKASSA_PRODUCTS["club1_ru"]
    session = YookassaPayment.create({
        "amount": {
            "value": product["amount"],
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": settings.APP_HOST + "/user/me/"
        },
        "capture": True,
        "description": f"{product['description']} для {user.email}",
        "metadata": {
            "email": user.email,
            "product": product["code"],
        },
        "receipt": {
            "customer": {
                "full_name": user.full_name,
                "email": user.email,
            },
            "items": [
                {
                    "description": product["description"],
                    "quantity": "1.00",
                    "amount": {
                        "value": product["amount"],
                        "currency": "RUB"
                    },
                    "payment_mode": "full_payment",
                    "payment_subject": "payment",
                    "vat_code": 1,
                },
            ]
        }
    }, uuid.uuid4())

    payment = Payment.create(
        reference=session.id,
        user=user,
        product=product,
        data=session.json(),
    )

    return render(request, "payments/rubles.html", {
        "user": user,
        "payment": payment,
        "session": session,
    })


def yookassa_webhook(request):
    try:
        webhook = parse_yookassa_webhook_event(request)
    except BadRequest as ex:
        return HttpResponse(ex.message, status=ex.code)

    log.info(f"YOOKASSA WEBHOOK: {webhook.json()}")

    if webhook.event == "payment.succeeded":
        user = User.objects.filter(email=webhook.object.metadata["email"]).first()

        try:
            payment = Payment.finish(
                reference=webhook.object.id,
                status=Payment.STATUS_SUCCESS,
                data=webhook.json(),
            )
        except PaymentException:
            return HttpResponse("[payment not found]", status=400)

        if not user:
            user = payment.user

        product = YOOKASSA_PRODUCTS["club1_ru"]
        product["activator"](product, payment, user)
        return HttpResponse("[ok]", status=200)

    return HttpResponse("[unknown event]", status=200)

