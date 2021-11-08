from datetime import datetime
from urllib.parse import urlencode, parse_qsl

from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import render, redirect
from django.urls import reverse

from auth.exceptions import PatreonException
from auth.helpers import set_session_cookie
from auth.models import Session
from auth.providers import patreon
from club import features
from common.feature_flags import feature_required
from users.models.user import User
from common.images import upload_image_from_url


@feature_required(features.PATREON_AUTH_ENABLED)
def patreon_login(request):
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


@feature_required(features.PATREON_AUTH_ENABLED)
def patreon_oauth_callback(request):
    code = request.GET.get("code")
    if not code:
        return render(request, "error.html", {
            "title": "Что-то сломалось между нами и патреоном",
            "message": "Так бывает. Попробуйте залогиниться еще раз"
        }, status=500)

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
            }, status=503)

        return render(request, "error.html", {
            "message": "Не получилось загрузить ваш профиль с серверов патреона. "
                       "Попробуйте еще раз, наверняка оно починится. "
                       f"Но если нет, то вот текст ошибки, с которым можно пожаловаться мне в личку:",
            "data": str(ex)
        }, status=504)

    membership = patreon.parse_active_membership(user_data)
    if not membership:
        return render(request, "error.html", {
            "title": "Надо быть патроном, чтобы состоять в Клубе",
            "message": "Кажется, вы не патроните <a href=\"https://www.patreon.com/join/vas3k\">@vas3k</a>. "
                       "А это одно из основных требований для входа в Клуб.<br><br>"
                       "Ещё иногда бывает, что ваш банк отказывает патреону в снятии денег. "
                       "Проверьте, всё ли там у них в порядке."
        }, status=402)

    now = datetime.utcnow()

    # get user by patreon_id or email
    user = User.objects.filter(Q(patreon_id=membership.user_id) | Q(email=membership.email.lower())).first()
    if not user:
        # user is new, create it
        try:
            user = User.objects.create(
                patreon_id=membership.user_id,
                email=membership.email.lower(),
                full_name=membership.full_name[:120],
                avatar=upload_image_from_url(membership.image) if membership.image else None,
                membership_platform_type=User.MEMBERSHIP_PLATFORM_PATREON,
                membership_started_at=membership.started_at,
                membership_expires_at=membership.expires_at,
                balance=membership.lifetime_support_cents / 100,
                created_at=now,
                updated_at=now,
                is_email_verified=False,
            )
        except IntegrityError:
            return render(request, "error.html", {
                "title": "💌 Придётся войти через почту",
                "message": "Пользователь с таким имейлом уже зарегистрирован, но не через патреон. "
                           "Чтобы защититься от угона аккаунтов через подделку почты на патреоне, "
                           "нам придётся сейчас попросить вас войти через почту."
            }, status=400)
    else:
        # user exists
        if user.deleted_at:
            return render(request, "error.html", {
                "title": "💀 Аккаунт был удалён",
                "message": "Войти через этот патреон больше не получится"
            }, status=404)

        # update membership dates
        user.balance = membership.lifetime_support_cents / 100  # TODO: remove when the real money comes in
        if membership.expires_at > user.membership_expires_at:
            user.membership_expires_at = membership.expires_at

    user.membership_platform_data = {
        "access_token": auth_data["access_token"],
        "refresh_token": auth_data["refresh_token"],
    }
    user.save()

    # create a new session token to authorize the user
    session = Session.create_for_user(user)
    redirect_to = reverse("profile", args=[user.slug])
    state = request.GET.get("state")
    if state:
        state_dict = dict(parse_qsl(state))
        if "goto" in state_dict:
            redirect_to = state_dict["goto"]

    response = redirect(redirect_to)
    return set_session_cookie(response, user, session)
