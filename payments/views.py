import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, redirect

from payments.models import Payment
from payments.products import PRODUCTS
from payments.service import stripe
from users.models.user import User

log = logging.getLogger()


def membership_expired(request):
    if not request.me:
        return redirect("index")

    if request.me.membership_expires_at >= datetime.utcnow():
        return redirect("profile", request.me.slug)

    return render(request, "payments/membership_expired.html")


def done(request):
    payment = Payment.get(reference=request.GET.get("reference"))
    return render(request, "payments/messages/done.html", {
        "payment": payment,
    })


def pay(request):
    product_code = request.GET.get("product_code")
    product = PRODUCTS.get(product_code)
    if not product:
        return render(request, "error.html", {
            "title": "Не выбран пакет 😣",
            "message": "Выберите что вы хотите купить или насколько пополнить свою карту"
        })

    # user authorized or we need to create a new one?
    if request.me:
        user = request.me
    else:
        email = request.GET.get("email") or ""
        if not email or "@" not in email:
            return render(request, "error.html", {
                "title": "Плохой e-mail адрес 😣",
                "message": "Нам ведь нужно будет как-то привязать ваш аккаунт к платежу"
            })

        now = datetime.utcnow()
        user, _ = User.objects.get_or_create(
            email=email,
            defaults=dict(
                membership_platform_type=User.MEMBERSHIP_PLATFORM_DIRECT,
                full_name=email[:email.find("@")],
                membership_started_at=now,
                membership_expires_at=now + timedelta(days=1),
                created_at=now,
                updated_at=now,
                moderation_status=User.MODERATION_STATUS_INTRO,
            ),
        )

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price": product["stripe_id"],
            "quantity": 1,
        }],
        customer_email=user.email,
        mode="payment",
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
    )

    payment = Payment.start(session.id, user, product)

    return render(request, "payments/pay.html", {
        "session": session,
        "product": product,
        "payment": payment,
        "user": user,
    })


def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not payload or not sig_header:
        return HttpResponse("[invalid payload]", status=400)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse("[invalid payload]", status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse("[invalid signature]", status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        payment = Payment.finish(
            reference=session["id"],
            status=Payment.PAYMENT_STATUS_SUCCESS,
            data=session,
        )
        product = PRODUCTS[payment.product_code]
        product["activator"](product, payment, payment.user)

    return HttpResponse("[ok]", status=200)
