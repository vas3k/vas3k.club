from datetime import datetime, timedelta
from urllib.parse import quote, urlparse, parse_qsl, urlencode

import jwt
from django.shortcuts import render, redirect
from django.urls import reverse

from auth.helpers import authorized_user
from auth.models import Apps


def external_login(request):
    goto = request.GET.get("redirect")
    if not goto:
        return render(request, "error.html", {"message": "Нужен параметр ?redirect"}, status=400)

    # check if user is logged in or redirect to login screen
    me = authorized_user(request)
    if not me:
        redirect_here_again = quote(reverse("external_login") + f"?redirect={goto}", safe="")
        return redirect(reverse("login") + f"?goto={redirect_here_again}")

    # we only authorize applications we know with the keys we set for them
    app_id = request.GET.get("app_id")
    app = Apps.objects.filter(id=app_id).first()
    if not app:
        return render(
            request, "error.html",
            {"message": "Неизвестное приложение, проверьте параметр ?app_id"},
            status=400
        )

    # check if redirect_url is in the list of allowed urls
    goto_parsed = urlparse(goto)
    goto_path_without_params = f"{goto_parsed.scheme}://{goto_parsed.netloc}{goto_parsed.path}"
    if goto_path_without_params not in app.redirect_urls:
        return render(
            request, "error.html",
            {"message": f"'{goto}' не находится в списке разрешеных redirect_urls для этого приложения"},
            status=400
        )

    # TODO: show "authorize" window and ask for user's consent here

    # success! issue a new signed JWT
    payload = {
        "user_slug": me.slug,
        "user_name": me.full_name,
        "user_email": me.email,
        "exp": datetime.utcnow() + timedelta(hours=app.jwt_expire_hours),
    }
    jwt_token = jwt.encode(payload, app.jwt_secret, app.jwt_algorithm).decode("utf-8")

    # add ?jwt= to redirect_url and activate the redirect
    goto_params = parse_qsl(goto_parsed.query)
    goto_params += [("jwt", jwt_token)]
    return redirect(f"{goto_path_without_params}?{urlencode(goto_params)}")
