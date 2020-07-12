import hashlib
import hmac
import json
import logging
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, redirect

log = logging.getLogger()


def membership_expired(request):
    if not request.me:
        return redirect("index")

    if request.me.membership_expires_at >= datetime.utcnow():
        return redirect("profile", request.me.slug)

    return render(request, "users/messages/membership_expired.html")


def adyen_callback(request):
    print(f"ADYEN CALLBACK: {request.body}")
    # success: {"live":"false","notificationItems":[{"NotificationRequestItem":{"additionalData":{"expiryDate":"03\\/2030","authCode":"066316","paymentLinkId":"PL67CAA834642A2AE7","recurring.recurringDetailReference":"8315945522101344","cardSummary":"1142","metadata.checkout.linkId":"PL67CAA834642A2AE7","recurringProcessingModel":"Subscription","recurring.shopperReference":"me@vas3k.ru"},"amount":{"currency":"EUR","value":4000},"eventCode":"AUTHORISATION","eventDate":"2020-07-12T15:03:13+02:00","merchantAccountCode":"VasilyZubarevBeratungECOM","merchantReference":"vas3k_club3_1594558824","operations":["CANCEL","CAPTURE","REFUND"],"paymentMethod":"visa","pspReference":"883594558993579B","reason":"066316:1142:03\\/2030","success":"true"}}]}
    # fail: {"live":"false","notificationItems":[{"NotificationRequestItem":{"additionalData":{"expiryDate":"12\/2012"," NAME1 ":"VALUE1","totalFraudScore":"10","cardSummary":"7777","NAME2":"  VALUE2  ","fraudCheck-6-ShopperIpUsage":"10"},"amount":{"currency":"EUR","value":10150},"eventCode":"AUTHORISATION","eventDate":"2020-07-12T12:58:40+02:00","merchantAccountCode":"VasilyZubarevBeratungECOM","merchantReference":"8313842560770001","paymentMethod":"visa","pspReference":"test_AUTHORISATION_3","reason":"REFUSED","success":"false"}}]}

    data = json.loads(request.body)

    hmac_hash = hmac.new(
        settings.ADIEN_HMAC,
        request.body,
        hashlib.sha256,
    ).hexdigest()
    if hmac_hash != data["notificationItems"][0]["NotificationRequestItem"]["additionalData"]["hmacSignature"]:
        return HttpResponse("Bad signature", status=400)

    return HttpResponse("[accepted]")
