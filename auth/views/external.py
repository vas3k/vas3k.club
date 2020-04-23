from datetime import datetime
from urllib.parse import quote

import jwt
from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse

from auth.helpers import authorized_user


def external(request):
    goto = request.GET.get("redirect")
    if not goto:
        return render(request, "error.html", {"message": "Нужен параметр ?redirect"})

    me = authorized_user(request)
    if not me:
        redirect_here_again = quote(reverse("external") + f"?redirect={goto}", safe="")
        return redirect(reverse("login") + f"?goto={redirect_here_again}")

    payload = {
        "user_id": me.id,
        "user_name": me.name,
        "exp": datetime.utcnow() + settings.JWT_EXP_TIMEDELTA,
    }
    jwt_token = jwt.encode(payload, settings.JWT_SECRET, settings.JWT_ALGORITHM).decode("utf-8")
    return redirect(f"{goto}?jwt={jwt_token}")
