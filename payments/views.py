import logging
import time
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, redirect

from payments.products import PRODUCTS
from payments.service import ady

log = logging.getLogger()


def membership_expired(request):
    if not request.me:
        return redirect("index")

    if request.me.membership_expires_at >= datetime.utcnow():
        return redirect("profile", request.me.slug)

    return render(request, "payments/membership_expired.html")


def pay(request):
    if request.me:
        email = request.me.email
        slug = request.me.slug
    else:
        email = request.GET.get("email")
        slug = email

    if not email or "@" not in email:
        return render(request, "error.html", {
            "title": "E-mail не указан 😣",
            "message": "Нам же нужно как-то понять за какой аккаунт вы платите"
        })

    product_code = request.GET.get("package")
    product = PRODUCTS.get(product_code)
    if not product:
        return render(request, "error.html", {
            "title": "Не выбран пакет 😣",
            "message": "Выберите насколько вы хотите пополнить свою карту"
        })

    payment_id = str(int(time.time()))
    try:
        payment_link = ady.client.call_checkout_api({
            "id": payment_id,
            "amount": {
                "value": int(product["amount"]) * 100,
                "currency": "EUR",
            },
            "description": product["description"],
            "merchantAccount": settings.ADYEN_MERCHANT_ACCOUNT,
            "reference": f"{slug}_{product_code}_{payment_id}",
            "shopperReference": email,
            "shopperEmail": email,
            "shopperLocale": settings.ADYEN_LOCALE,
            "status": "active",
            "returnUrl": product["return_url"],
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
