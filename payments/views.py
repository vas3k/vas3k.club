from datetime import datetime

from django.shortcuts import render, redirect


def membership_expired(request):
    if not request.me:
        return redirect("index")

    if request.me.membership_expires_at >= datetime.utcnow():
        return redirect("profile", request.me.slug)

    return render(request, "users/messages/membership_expired.html")
