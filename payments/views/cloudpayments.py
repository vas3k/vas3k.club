import json
import logging
from datetime import datetime

from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render

from authn.decorators.auth import require_auth
from payments.cloudpayments import CLOUDPAYMENTS_PRODUCTS, CloudPaymentsService, TransactionStatus
from payments.models import Payment, Subscription
from users.models.user import User

log = logging.getLogger(__name__)


def done(request):
    payment = Payment.get(reference=request.GET.get("reference"))
    return render(request, "payments/messages/done.html", {
        "payment": payment,
    })


def pay(request):
    product_code = request.GET.get("product_code")
    is_invite = request.GET.get("is_invite")
    # is_recurrent = request.GET.get("is_recurrent")
    is_recurrent = True
    if product_code == "club180":
        is_recurrent = False
    if is_recurrent:
        product_code = f"{product_code}_recurrent"

    # find product by code
    product = CLOUDPAYMENTS_PRODUCTS.get(product_code)
    if not product:
        return render(request, "error.html", {
            "title": "Что-то пошло не так 😣",
            "message": "Мы не поняли, что вы хотите купить или насколько пополнить свою карту. <br/><br/>" +
                       "А, может, просто не нашли <b>" + product_code + "</b> в нашем ассортементе"
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

    # create stripe session and payment (to keep track of history)
    pay_service = CloudPaymentsService()
    invoice = pay_service.create_payment(product_code, user)

    payment = Payment.create(
        reference=invoice.id,
        user=user,
        product=product,
        data=payment_data,
    )

    return render(request, "payments/cloudpayments_pay.html", {
        "invoice": invoice,
        "product": product,
        "payment": payment,
        "user": user,
    })


def cloudpayments_webhook(request):
    pay_service = CloudPaymentsService()
    is_verified = pay_service.verify_webhook(request)

    if not is_verified:
        log.error("Request is not verified %r", request.POST)
        return HttpResponseBadRequest("Request is not verified")

    action = request.GET["action"]
    payload = request.POST

    log.info("Webhook action %s, payload %s", action, payload)

    if action == "recurrent" and payload["Status"] == "Cancelled":
        Subscription.objects.filter(subscription_id=payload["Id"]).update(status=Subscription.STATUS_STOPPED)
        return HttpResponse(json.dumps({"code": 0}))

    status, answer = pay_service.accept_payment(action, payload)

    if status != TransactionStatus.APPROVED:
        return HttpResponse(json.dumps(answer))

    if payload.get("InvoiceId"):
        log.info("Payment %s is finished", payload["InvoiceId"])
        payment = Payment.finish(
            reference=payload["InvoiceId"],
            status=Payment.STATUS_SUCCESS,
            data=payload,
        )

        product = CLOUDPAYMENTS_PRODUCTS[payment.product_code]
        product["activator"](product, payment, payment.user)

        if payload.get("SubscriptionId"):
            Subscription.objects.create(
                user=payment.user,
                subscription_id=payload["SubscriptionId"],
                product_code=payment.product_code,
                amount=payment.amount,
                data=json.dumps(payload),
                reference=payload["InvoiceId"],
            )

    else:
        log.info("Subscription payment %s is finished", payload["SubscriptionId"])
        subscription = Subscription.objects.get(subscription_id=payload["SubscriptionId"])

        product = CLOUDPAYMENTS_PRODUCTS[subscription.product_code]
        payment = Payment.objects.create(
            reference=subscription.reference,
            user=subscription.user,
            product_code=subscription.product_code,
            amount=product.get("amount") or 0.0,
            status=Payment.STATUS_SUCCESS,
            data=json.dumps(payload),
        )

        product["activator"](product, payment, payment.user)

    return HttpResponse(json.dumps(answer))


@require_auth
def stop_cloudpayment_subscription(request, subscription_id):
    pay_service = CloudPaymentsService()

    try:
        pay_service.stop_subscription(subscription_id)
    except Exception as e:
        log.exception("Cannot stop subscription %s: %s", subscription_id, e)
        return render(request, "error.html", {
            "title": "Подписка не найдена",
            "message": "В нашей базе нет подписки с таким ID"
        })

    return render(request, "payments/messages/subscription_stopped.html")
