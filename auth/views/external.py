from datetime import datetime
from urllib.parse import quote

import jwt
from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse

from auth.helpers import authorized_user


def external_login(request):
    goto = request.GET.get("redirect")
    if not goto:
        return render(request, "error.html", {"message": "Нужен параметр ?redirect"})

    me = authorized_user(request)
    if not me:
        redirect_here_again = quote(reverse("external") + f"?redirect={goto}", safe="")
        return redirect(reverse("login") + f"?goto={redirect_here_again}")

    # TODO: it would be nice to show "authorize" window here

    payload = {
        "user_slug": me.slub,
        "user_full_name": me.full_name,
        "exp": datetime.utcnow() + settings.JWT_EXP_TIMEDELTA,
    }
    jwt_token = jwt.encode(payload, settings.JWT_SECRET, settings.JWT_ALGORITHM).decode("utf-8")
    return redirect(f"{goto}?jwt={jwt_token}")
