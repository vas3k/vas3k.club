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
        redirect_here_again = quote(reverse("external_login") + f"?redirect={goto}", safe="")
        return redirect(reverse("login") + f"?goto={redirect_here_again}")

    # TODO: it would be nice to show "authorize" window here

    payload = {
        "user_slug": me.slug,
        "user_name": me.full_name,
        "user_email": me.email,
        "exp": datetime.utcnow() + settings.JWT_EXP_TIMEDELTA,
    }

    jwt_token = jwt.encode(payload, settings.JWT_PRIVATE_KEY, settings.JWT_ALGORITHM).decode("utf-8")

    # TODO: implement proper url parsing + domain validation + query building
    if "?" in goto:
        goto += f"&jwt={jwt_token}"
    else:
        goto += f"?jwt={jwt_token}"

    return redirect(goto)
