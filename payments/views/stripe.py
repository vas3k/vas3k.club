import logging
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

from authn.decorators.auth import require_auth
from club.exceptions import BadRequest
from payments.exceptions import PaymentException
from payments.helpers import parse_stripe_webhook_event
from payments.models import Payment
from payments.products import PRODUCTS, find_by_stripe_id
from payments.service import stripe
from users.models.user import User

log = logging.getLogger()


def done(request):
    payment = Payment.get(reference=request.GET.get("reference"))
    return render(request, "payments/messages/done.html", {
        "payment": payment,
    })


def pay(request):
    product_code = request.GET.get("product_code")
    is_invite = request.GET.get("is_invite")
    is_recurrent = request.GET.get("is_recurrent")
    if is_recurrent:
        product_code = f"{product_code}_recurrent_yearly"

    # find product by code
    product = PRODUCTS.get(product_code)
    if not product:
        return render(request, "error.html", {
            "title": "Не выбран пакет 😣",
            "message": "Выберите что вы хотите купить или насколько пополнить свою карту"
        })

    # filter our legacy products
    if product_code.startswith("legacy"):
        return render(request, "error.html", {
            "title": "Это устаревший тариф ☠️",
            "message": "По этому коду больше нельзя совершать покупки, выберите другой"
        })

    payment_data = {}
    now = datetime.utcnow()

    # parse email
    email = request.GET.get("email") or ""
    if email:
        email = email.lower()

    # who's paying?
    if not request.me:  # scenario 1: new user
        if not email or "@" not in email:
            return render(request, "error.html", {
                "title": "Плохой e-mail адрес 😣",
                "message": "Нам ведь нужно будет как-то привязать аккаунт к платежу"
            })

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
    elif is_invite:  # scenario 2: invite a friend
        if not email or "@" not in email:
            return render(request, "error.html", {
                "title": "Плохой e-mail адрес друга 😣",
                "message": "Нам ведь нужно будет куда-то выслать инвайт"
            })

        _, is_created = User.objects.get_or_create(
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

        user = request.me
        payment_data = {
            "invite": email,
            "is_created": is_created,
        }
    else:  # scenario 3: account renewal
        user = request.me

    # reuse stripe customer ID if user already has it
    if user.stripe_id:
        customer_data = dict(
            customer=user.stripe_id,
            customer_update={
                "address": "auto",
                "shipping": "auto",
            }
        )
    else:
        customer_data = dict(customer_email=user.email)

    # create stripe session and payment (to keep track of history)
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price": product["stripe_id"],
            "quantity": 1,
        }],
        **customer_data,
        mode="subscription" if is_recurrent else "payment",
        metadata=payment_data,
        automatic_tax={"enabled": True},
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
    )

    payment = Payment.create(
        reference=session.id,
        user=user,
        product=product,
        data=payment_data,
    )

    return render(request, "payments/pay.html", {
        "session": session,
        "product": product,
        "payment": payment,
        "user": user,
    })


@require_auth
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
    try:
        event = parse_stripe_webhook_event(request, settings.STRIPE_WEBHOOK_SECRET)
    except BadRequest as ex:
        return HttpResponse(ex.message, status=ex.code)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        try:
            payment = Payment.finish(
                reference=session["id"],
                status=Payment.STATUS_SUCCESS,
                data=session,
            )
        except PaymentException:
            return HttpResponse("[payment not found]", status=400)

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
            product=find_by_stripe_id(invoice["lines"]["data"][0]["plan"]["id"]),
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

