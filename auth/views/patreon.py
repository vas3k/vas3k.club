from datetime import datetime
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse

from auth.exceptions import PatreonException
from auth.helpers import authorized_user
from auth.models import Session
from auth.providers import patreon
from users.models import User
from utils.date import first_day_of_next_month
from utils.images import upload_image_from_url
from utils.strings import random_string


def patreon_login(request):
    user = authorized_user(request)
    if user:
        return redirect("profile", user.slug)

    state = {}
    goto = request.GET.get("goto")
    if goto:
        state["goto"] = goto

    query_string = urlencode(
        {
            "response_type": "code",
            "client_id": settings.PATREON_CLIENT_ID,
            "redirect_uri": settings.PATREON_REDIRECT_URL,
            "scope": settings.PATREON_SCOPE,
            "state": urlencode(state) if state else "",
        }
    )
    return redirect(f"{settings.PATREON_AUTH_URL}?{query_string}")


def patreon_oauth_callback(request):
    code = request.GET.get("code")
    if not code:
        return render(request, "error.html", {
            "message": "Что-то сломалось между нами и патреоном. Так бывает. Попробуйте залогиниться еще раз."
        })

    try:
        auth_data = patreon.fetch_auth_data(code)
        user_data = patreon.fetch_user_data(auth_data["access_token"])
    except PatreonException as ex:
        if "invalid_grant" in str(ex):
            return render(request, "error.html", {
                "message": "Тут такое дело. Авторизация патреона — говно. "
                           "Она не сразу понимает, что вы стали моим патроном и отдаёт мне ошибку. "
                           "Я уже написал им в саппорт, но пока вам надо немного подождать и авторизоваться снова. "
                           "Обычно тогда срабатывает. Если нет — напишите мне в личные сообщения на патреоне."
            })

        return render(request, "error.html", {
            "message": "Не получилось загрузить ваш профиль с серверов патреона. "
                       "Попробуйте еще раз, наверняка оно починится. "
                       f"Но если нет, то вот текст ошибки, с которым можно пожаловаться мне в личку:",
            "data": str(ex)
        })

    membership = patreon.parse_active_membership(user_data)
    if not membership:
        return render(request, "error.html", {
            "message": "Надо быть патроном чтобы состоять в клубе.<br>"
                       '<a href="https://www.patreon.com/join/vas3k">Станьте им здесь!</a>'
        })

    now = datetime.utcnow()
    user, is_created = User.objects.get_or_create(
        membership_platform_type=User.MEMBERSHIP_PLATFORM_PATREON,
        membership_platform_id=membership.user_id,
        defaults=dict(
            email=membership.email,
            full_name=membership.full_name[:120],
            avatar=upload_image_from_url(membership.image) if membership.image else None,
            membership_started_at=membership.started_at,
            membership_expires_at=membership.expires_at,
            created_at=now,
            updated_at=now,
            is_email_verified=False,
            is_profile_complete=False,  # redirect new users to an intro page
        ),
    )

    if is_created:
        user.balance = membership.lifetime_support_cents / 100
    else:
        user.membership_expires_at = membership.expires_at
        user.balance = membership.lifetime_support_cents / 100  # TODO: remove when the real money comes in

    user.membership_platform_data = {
        "access_token": auth_data["access_token"],
        "refresh_token": auth_data["refresh_token"],
    }
    user.save()

    session = Session.objects.create(
        user=user,
        token=random_string(length=32),
        created_at=now,
        expires_at=first_day_of_next_month(now),
    )

    redirect_to = reverse("profile", args=[user.slug])

    state = request.GET.get("state")
    if state:
        redirect_to += f"?{state}"

    response = redirect(redirect_to)
    response.set_cookie(
        key="token",
        value=session.token,
        max_age=settings.SESSION_COOKIE_AGE,
        httponly=True,
        secure=not settings.DEBUG,
    )
    return response
