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
    log.info(f"ADYEN CALLBACK: {request.body}")
    return HttpResponse("OK")
