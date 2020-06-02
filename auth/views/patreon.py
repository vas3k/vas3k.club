from datetime import datetime
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse

from auth.exceptions import PatreonException
from auth.helpers import authorized_user
from auth.models import Session
from auth.providers import patreon
from users.models.user import User
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
            "title": "Что-то сломалось между нами и патреоном",
            "message": "Так бывает. Попробуйте залогиниться еще раз"
        })

    try:
        auth_data = patreon.fetch_auth_data(code)
        user_data = patreon.fetch_user_data(auth_data["access_token"])
    except PatreonException as ex:
        if "invalid_grant" in str(ex):
            return render(request, "error.html", {
                "title": "Тут такое дело 😭",
                "message": "Авторизация патреона — говно. "
                           "Она не сразу понимает, что вы стали патроном и отдаёт "
                           "статус «отказано» в первые несколько минут, а иногда и часов. "
                           "Я уже написал им в саппорт, но пока вам надо немного подождать и авторизоваться снова. "
                           "Если долго не будет пускать — напишите мне в личку на патреоне."
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
            "title": "Надо быть патроном, чтобы состоять в Клубе",
            "message": "Кажется, вы не патроните <a href=\"https://www.patreon.com/join/vas3k\">@vas3k</a>. "
                       "А это одно из основных требований для входа в Клуб.<br><br>"
                       "Ещё иногда бывает, что ваш банк отказывает патреону в снятии денег. "
                       "Проверьте, всё ли там у них в порядке."
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
        expires_at=user.membership_expires_at,
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
