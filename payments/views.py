import json
import logging
from datetime import datetime, timedelta
from urllib.parse import quote

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
            "message": "Выберите что вы хотите купить или насколько пополнить свою карту"
        })

    # user authorized or we need to create a new one?
    if request.me:
        user = request.me
    else:
        email = request.GET.get("email")
        if email and "@" not in email:
            return render(request, "error.html", {
                "title": "Плохой e-mail адрес 😣",
                "message": "Нам ведь нужно будет как-то привязать ваш аккаунт к платежу"
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

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "eur",
                "product_data": {
                    "name": product["description"],
                },
                "unit_amount": int(product["amount"]) * 100,
            },
            "quantity": 1,
        }],
        customer_email=user.email,
        mode="payment",
        success_url=product["return_url"] + f"?reference={quote(payment.reference)}",
        cancel_url=settings.APP_HOST,
    )

    return render(request, "payments/pay.html", {
        "session": session,
        "product": product,
        "user": user,
    })


# def adyen_callback(request):
#     print(f"ADYEN CALLBACK: {request.body}")
#     # success: {"live":"false","notificationItems":[{"NotificationRequestItem":{"additionalData":{"expiryDate":"03\\/2030","authCode":"040148","paymentLinkId":"PLCB37868FA2F60E24","recurring.recurringDetailReference":"8315945522101344","cardSummary":"1142","metadata.checkout.linkId":"PLCB37868FA2F60E24","recurringProcessingModel":"Subscription","recurring.shopperReference":"me@vas3k.ru","hmacSignature":"iucKmIhDArxQ+x9RXfk8yrh0XL7UyyMYvfKJJ8bTd1I="},"amount":{"currency":"EUR","value":4000},"eventCode":"AUTHORISATION","eventDate":"2020-07-12T15:17:43+02:00","merchantAccountCode":"VasilyZubarevBeratungECOM","merchantReference":"vas3k_club3_1594559849","operations":["CANCEL","CAPTURE","REFUND"],"paymentMethod":"visa","pspReference":"852594559862935G","reason":"040148:1142:03\\/2030","success":"true"}}]}
#     # fail: {"live":"false","notificationItems":[{"NotificationRequestItem":{"additionalData":{"expiryDate":"12\/2012"," NAME1 ":"VALUE1","totalFraudScore":"10","cardSummary":"7777","NAME2":"  VALUE2  ","fraudCheck-6-ShopperIpUsage":"10"},"amount":{"currency":"EUR","value":10150},"eventCode":"AUTHORISATION","eventDate":"2020-07-12T12:58:40+02:00","merchantAccountCode":"VasilyZubarevBeratungECOM","merchantReference":"8313842560770001","paymentMethod":"visa","pspReference":"test_AUTHORISATION_3","reason":"REFUSED","success":"false"}}]}
#
#     data = json.loads(request.body)
#     for notification in data["notificationItems"]:
#         item = notification["NotificationRequestItem"]
#         if not Adyen.util.is_valid_hmac_notification(item, settings.ADYEN_HMAC):
#             return HttpResponse("bad signature")
#
#         if not item["success"]:
#             Payment.finish(
#                 reference=item["merchantReference"],
#                 status=Payment.PAYMENT_STATUS_FAILED,
#                 data=item,
#             )
#
#         payment = Payment.finish(
#             reference=item["merchantReference"],
#             status=Payment.PAYMENT_STATUS_SUCCESS,
#             data=item,
#         )
#         product = PRODUCTS[payment.product_code]
#         product["activator"](product, payment, payment.user)
#
#     return HttpResponse("[accepted]")
