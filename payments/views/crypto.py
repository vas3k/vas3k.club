import hashlib
import hmac
import json
import logging
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import render

from payments.exceptions import PaymentNotFound, PaymentAlreadyFinalized
from payments.models import Payment
from payments.products import PRODUCTS, find_by_coinbase_id
from users.models.user import User

log = logging.getLogger()


def crypto(request):
    raise Http404()  # turned off

    product_code = request.GET.get("product_code") or "club1"

    # find product by code
    product = PRODUCTS.get(product_code)
    if not product:
        return render(request, "error.html", {
            "title": "Не выбран пакет 😣",
            "message": "Выберите что вы хотите купить или насколько пополнить свою карту"
        })

    # is it possible to buy it with crypto?
    if not product.get("coinbase_id"):
        return render(request, "error.html", {
            "title": "За это нельзя платить криптой 😣",
            "message": "Криптой пока можно только продлять себе аккаунт, "
                       "инвайты и прочие фичи пока не поддерживаются"
        })

    return render(request, "payments/crypto.html", {
        "product": product,
        "email": request.me.email if request.me else request.GET.get("email"),
        "user": request.me,
    })


def coinbase_webhook(request):
    payload = request.body
    webhook_signature = request.META.get("HTTP_X_CC_WEBHOOK_SIGNATURE")
    if not payload or not webhook_signature:
        return HttpResponse("[invalid payload]", status=400)

    # verify webhook signature
    payload_signature = hmac.new(
        key=bytes(settings.COINBASE_WEBHOOK_SECRET, "utf-8"),
        msg=payload,  # it's already in bytes
        digestmod=hashlib.sha256
    ).hexdigest()
    if payload_signature.upper() != webhook_signature.upper():
        return HttpResponse("[bad signature]", status=400)

    # load event data
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return HttpResponse("[payload is not json]", status=400)

    event = data.get("event")
    event_type = event.get("type")
    event_data = event.get("data")
    event_code = event_data.get("code")
    if not event or not event_type or not event_data or not event_code:
        return HttpResponse("[bad payload structure]", status=400)

    log.info(f"Coinbase webhook event: {event_type} ({event_code})")

    # find or create the user
    metadata_email = event_data.get("metadata", {}).get("email")
    if not metadata_email:
        return HttpResponse("[no email in payload]", status=400)

    now = datetime.utcnow()
    user, _ = User.objects.get_or_create(
        email=metadata_email,
        defaults=dict(
            membership_platform_type=User.MEMBERSHIP_PLATFORM_CRYPTO,
            full_name=metadata_email[:metadata_email.find("@")],
            membership_started_at=now,
            membership_expires_at=now,
            created_at=now,
            updated_at=now,
            moderation_status=User.MODERATION_STATUS_INTRO,
        ),
    )

    # find product
    checkout_id = event_data.get("checkout", {}).get("id")
    product = find_by_coinbase_id(checkout_id)
    if not checkout_id or not product:
        return HttpResponse("[product not found]", status=404)

    # make actions for event_types
    if event_type == "charge:created":
        Payment.create(
            reference=event_code,
            user=user,
            product=product,
            data=event,
            status=Payment.STATUS_STARTED,
        )
        return HttpResponse("[ok]", status=200)

    elif event_type == "charge:confirmed":
        try:
            payment = Payment.finish(
                reference=event_code,
                status=Payment.STATUS_SUCCESS,
                data=event,
            )
        except PaymentNotFound:
            payment = Payment.create(
                reference=event_code,
                user=user,
                product=product,
                data=event,
                status=Payment.STATUS_SUCCESS,
            )
        except PaymentAlreadyFinalized:
            return HttpResponse("[duplicate payment]", status=400)

        product["activator"](product, payment, user)
        return HttpResponse("[ok]", status=200)

    elif event_type == "charge:failed":
        Payment.finish(
            reference=event_code,
            status=Payment.STATUS_FAILED,
            data=event,
        )
        return HttpResponse("[ok]", status=200)

    elif event_type == "charge:pending":
        return HttpResponse("[ok]", status=200)

    return HttpResponse("[unknown event]", status=400)
