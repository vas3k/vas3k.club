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


def stripe_webhook(request):
    payload = request.body
    sig_header = request.META["HTTP_STRIPE_SIGNATURE"]
    print(f"STRIPE PAYLOAD: {payload}")
    print(f"STRIPE SIG: {sig_header}")
    return HttpResponse("[accepted]")
