from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import render, redirect

from authn.decorators.auth import require_auth
from authn.exceptions import PatreonException
from authn.providers import patreon
from club import features
from common.feature_flags import require_feature
from users.models.user import User


@require_auth
@require_feature(features.PATREON_AUTH_ENABLED)
def patreon_sync(request):
    query_string = urlencode(
        {
            "response_type": "code",
            "client_id": settings.PATREON_CLIENT_ID,
            "redirect_uri": settings.PATREON_REDIRECT_URL,
            "scope": settings.PATREON_SCOPE,
        }
    )
    return redirect(f"{settings.PATREON_AUTH_URL}?{query_string}")


@require_auth
@require_feature(features.PATREON_AUTH_ENABLED)
def patreon_sync_callback(request):
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

    if request.me.email.lower() != membership.email.lower():
        # user and patreon emails do not match
        return render(request, "error.html", {
            "title": "⛔️ Ваш email не совпадает с патреоновским",
            "message": f"Для продления аккаунта ваш адрес почты в Клубе и на Патреоне должен совпадать.<br><br> "
                       f"Сейчас там {membership.email}, а здесь {request.me.email}.<br><br> "
                       "Так нельзя, ибо это открывает дыру для продления сразу нескольким людям :)"
        }, status=400)

    if request.me.membership_platform_type != User.MEMBERSHIP_PLATFORM_PATREON:
        # wrong platform
        return render(request, "error.html", {
            "title": "⛔️ Вы не легаси-пользователь",
            "message": "Патреон — это старый метод входа. Он оставлен исключительно для олдов, "
                       "которые подписались много лет назад и не хотят никуда переезжать. "
                       "По нашим данным, вы уже перешли на более совершенный вид оплаты и вернуться назад не получится."
        }, status=400)

    # update membership dates
    if membership.expires_at > request.me.membership_expires_at:
        request.me.membership_expires_at = membership.expires_at
    request.me.save()

    return redirect("profile", request.me.slug)
