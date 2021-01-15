import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, redirect

from auth.helpers import auth_required
from payments.models import Payment
from payments.products import PRODUCTS, find_by_price_id, TAX_RATE_VAT
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
    is_recurrent = request.GET.get("is_recurrent")
    if is_recurrent:
        interval = request.GET.get("recurrent_interval") or "yearly"
        product_code = f"{product_code}_recurrent_{interval}"

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

        email = email.lower()
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

    if user.stripe_id:
        customer_data = dict(customer=user.stripe_id)
    else:
        customer_data = dict(customer_email=user.email)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price": product["stripe_id"],
            "quantity": 1,
            "tax_rates": [TAX_RATE_VAT],
        }],
        **customer_data,
        mode="subscription" if is_recurrent else "payment",
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
    )

    payment = Payment.create(session.id, user, product)

    return render(request, "payments/pay.html", {
        "session": session,
        "product": product,
        "payment": payment,
        "user": user,
    })


@auth_required
def stop_subscription(request, subscription_id):
    try:
        stripe.Subscription.delete(subscription_id)
    except stripe.error.NameError:
        return render(request, "error.html", {
            "title": "Подписка не найдена",
            "message": "В нашей базе нет подписки с таким ID"
        })
    except stripe.error.InvalidRequestError:
        return render(request, "error.html", {
            "title": "Подписка уже отменена 👌",
            "message": "Stripe сказал, что эта подписка уже отменена, так что всё ок"
        })

    return render(request, "payments/messages/subscription_stopped.html")


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

    log.info("Stripe webhook event: " + event["type"])

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        payment = Payment.finish(
            reference=session["id"],
            status=Payment.STATUS_SUCCESS,
            data=session,
        )
        # todo: do we need throw error in case payment not found?
        product = PRODUCTS[payment.product_code]
        product["activator"](product, payment, payment.user)
        return HttpResponse("[ok]", status=200)

    if event["type"] == "invoice.paid":
        invoice = event["data"]["object"]
        if invoice["billing_reason"] == "subscription_create":
            # already processed in "checkout.session.completed" event
            return HttpResponse("[ok]", status=200)

        user = User.objects.filter(stripe_id=invoice["customer"]).first()
        # todo: do we need throw error in case user not found?
        payment = Payment.create(
            reference=invoice["id"],
            user=user,
            product=find_by_price_id(invoice["lines"]["data"][0]["plan"]["id"]),
            data=invoice,
            status=Payment.STATUS_SUCCESS,
        )
        product = PRODUCTS[payment.product_code]
        product["activator"](product, payment, user)
        return HttpResponse("[ok]", status=200)

    if event["type"] in {"customer.created", "customer.updated"}:
        customer = event["data"]["object"]
        User.objects.filter(email=customer["email"]).update(stripe_id=customer["id"])
        return HttpResponse("[ok]", status=200)

    return HttpResponse("[unknown event]", status=400)
