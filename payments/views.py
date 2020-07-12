import json
import logging
from datetime import datetime, timedelta
from urllib.parse import quote

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, redirect

from payments.models import Payment
from payments.products import PRODUCTS
from payments.service import ady
from users.models.user import User

log = logging.getLogger()


def membership_expired(request):
    if not request.me:
        return redirect("index")

    if request.me.membership_expires_at >= datetime.utcnow():
        return redirect("profile", request.me.slug)

    return render(request, "payments/membership_expired.html")


def done(request):
    reference = request.GET.get("reference")
    payment = Payment.get(reference)
    return render(request, "payments/messages/done.html", {
        "payment": payment,
    })


def pay(request):
    product_code = request.GET.get("product_code")
    product = PRODUCTS.get(product_code)
    if not product:
        return render(request, "error.html", {
            "title": "Не выбран пакет 😣",
            "message": "Выберите насколько вы хотите пополнить свою карту"
        })

    # user authorized or we need to create a new one?
    if request.me:
        user = request.me
    else:
        email = request.GET.get("email")
        if email and "@" not in email:
            return render(request, "error.html", {
                "title": "Плохой e-mail адрес 😣",
                "message": "Нам ведь нужно будет как-то создать вам аккаунт"
            })

        now = datetime.utcnow()
        user, _ = User.objects.get_or_create(
            email=email,
            defaults=dict(
                membership_platform_type=User.MEMBERSHIP_PLATFORM_DIRECT,
                full_name=email.replace("@", " "),
                membership_started_at=now,
                membership_expires_at=now + timedelta(days=1),
                created_at=now,
                updated_at=now,
                moderation_status=User.MODERATION_STATUS_INTRO,
            ),
        )

    payment = Payment.start(user, product)

    try:
        payment_link = ady.client.call_checkout_api({
            "id": str(payment.id),
            "amount": {
                "value": int(product["amount"]) * 100,
                "currency": "EUR",
            },
            "description": product["description"],
            "merchantAccount": settings.ADYEN_MERCHANT_ACCOUNT,
            "reference": payment.reference,
            "shopperReference": user.email,
            "shopperEmail": user.email,
            "shopperLocale": settings.ADYEN_LOCALE,
            "status": "active",
            "returnUrl": product["return_url"] + f"?reference={quote(payment.reference)}",
        }, "paymentLinks")
    except AdyenError as ex:
        return render(request, "error.html", {
            "title": "Ошибка создания платежа. Напишите нам в саппорт :(",
            "message": f"{ex}: {ex.message}"
        })

    return redirect(payment_link.message["url"])


def stripe_webhook(request):
    payload = request.body
    sig_header = request.META["HTTP_STRIPE_SIGNATURE"]
    print(f"STRIPE PAYLOAD: {payload}")
    print(f"STRIPE SIG: {sig_header}")
    return HttpResponse("[accepted]")
