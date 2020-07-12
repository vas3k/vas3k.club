import logging
from datetime import datetime

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
    # success: {"live":"false","notificationItems":[{"NotificationRequestItem":{"additionalData":{"expiryDate":"12\/2012"," NAME1 ":"VALUE1","authCode":"1234","cardSummary":"7777","totalFraudScore":"10","NAME2":"  VALUE2  ","fraudCheck-6-ShopperIpUsage":"10"},"amount":{"currency":"EUR","value":10100},"eventCode":"AUTHORISATION","eventDate":"2020-07-12T12:58:40+02:00","merchantAccountCode":"VasilyZubarevBeratungECOM","merchantReference":"8313842560770001","operations":["CANCEL","CAPTURE","REFUND"],"paymentMethod":"visa","pspReference":"test_AUTHORISATION_1","reason":"1234:7777:12\/2012","success":"true"}}]}
    # fail: {"live":"false","notificationItems":[{"NotificationRequestItem":{"additionalData":{"expiryDate":"12\/2012"," NAME1 ":"VALUE1","totalFraudScore":"10","cardSummary":"7777","NAME2":"  VALUE2  ","fraudCheck-6-ShopperIpUsage":"10"},"amount":{"currency":"EUR","value":10150},"eventCode":"AUTHORISATION","eventDate":"2020-07-12T12:58:40+02:00","merchantAccountCode":"VasilyZubarevBeratungECOM","merchantReference":"8313842560770001","paymentMethod":"visa","pspReference":"test_AUTHORISATION_3","reason":"REFUSED","success":"false"}}]}
    return HttpResponse("OK")
