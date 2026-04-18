import logging
from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import render

from users.models.user import User

log = logging.getLogger()


def pay_yookassa(request):
    now = datetime.utcnow()

    if not request.me:  # scenario 1: new user
        # parse email
        email = request.GET.get("email") or ""
        if email:
            email = email.lower().strip()

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
    else:  # scenario 2: account renewal or invite purchase
        user = request.me

    return render(request, "payments/yookassa/pay.html", {
        "user": user,
    })


def yookassa_webhook(request):
    payload = request.body

    print(payload)
    log.error(payload)

    # if event["type"] == "invoice.paid":
    #     invoice = event["data"]["object"]
    #     user = User.objects.filter(stripe_id=invoice["customer"]).first()
    #     payment = Payment.create(
    #         reference=invoice["id"],
    #         user=user,
    #         product=find_by_stripe_id(invoice["lines"]["data"][0]["plan"]["id"]),
    #         data=invoice,
    #         status=Payment.STATUS_SUCCESS,
    #     )
    #     product = PRODUCTS[payment.product_code]
    #     product["activator"](product, payment, user)
    #     return HttpResponse("[ok]", status=200)

    return HttpResponse("[unknown event]", status=400)

