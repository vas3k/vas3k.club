import base64
import binascii
import hashlib
import hmac
import json

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpResponse
from django.shortcuts import render, get_object_or_404

from authn.decorators.auth import require_auth
from club.exceptions import AccessDenied, NotFound

from authn.decorators.api import api
from notifications.digests import generate_daily_digest, generate_weekly_digest
from users.models.user import User


def email_confirm(request, user_id, secret):
    try:
        # new emails use base64-encoded secret, old ones have it raw
        secret = base64.b64decode(secret.encode("utf-8")).decode()
    except (binascii.Error, UnicodeDecodeError):
        pass

    user = get_object_or_404(User, id=user_id, secret_hash=secret, deleted_at__isnull=True)
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])

    return render(request, "message.html", {
        "title": "💌 Ваш адрес почты подтвержден",
        "message": "Теперь туда будет приходить еженедельный журнал Клуба и другие оповещалки."
    })


def email_unsubscribe(request, user_id, secret):
    try:
        # new emails use base64-encoded secret, old ones have it raw
        secret = base64.b64decode(secret.encode("utf-8")).decode()
    except (binascii.Error, UnicodeDecodeError):
        pass

    user = get_object_or_404(User, id=user_id, secret_hash=secret, deleted_at__isnull=True)

    user.is_email_unsubscribed = True
    user.email_digest_type = User.EMAIL_DIGEST_TYPE_NOPE
    user.save(update_fields=["is_email_unsubscribed", "email_digest_type"])

    return render(request, "message.html", {
        "title": "🙅‍♀️ Вы отписались от всех писем Клуба",
        "message": "Мы ценим ваше время, потому отписали вас от всего и полностью. "
                   "Вы больше не получите от нас никаких писем. "
                   "Если захотите подписаться заново — напишите нам в поддержку."
    })


def email_digest_switch(request, digest_type, user_id, secret):
    try:
        # new emails use base64-encoded secret, old ones have it raw
        secret = base64.b64decode(secret.encode("utf-8")).decode()
    except (binascii.Error, UnicodeDecodeError):
        pass

    user = get_object_or_404(User, id=user_id, secret_hash=secret, deleted_at__isnull=True)

    if not dict(User.EMAIL_DIGEST_TYPES).get(digest_type):
        raise Http404()

    user.email_digest_type = digest_type
    user.is_email_unsubscribed = False
    user.save(update_fields=["email_digest_type", "is_email_unsubscribed"])

    if digest_type == User.EMAIL_DIGEST_TYPE_DAILY:
        return render(request, "message.html", {
            "title": "🔥 Теперь вы будете получать дейли-дайджест",
            "message": "Офигенно. "
                       "Теперь каждое утро вам будет приходить ваша персональная подборка всего нового в Клубе."
        })
    elif digest_type == User.EMAIL_DIGEST_TYPE_WEEKLY:
        return render(request, "message.html", {
            "title": "📅 Теперь вы получаете только еженедельный журнал",
            "message": "Раз в неделю вам будет приходить подборка лучшего контента в Клубе за эту неделю, "
                       "а также важные новости, вроде изменения правил. "
                       "Это удобно, качественно и не отнимает ваше время."
        })
    elif digest_type == User.EMAIL_DIGEST_TYPE_NOPE:
        return render(request, "message.html", {
            "title": "🙅‍♀️ Вы отписались от рассылок Клуба",
            "message": "Мы ценим ваше время, потому отписали вас от наших рассылок контента. "
                       "Можете следить за новыми постами в телеграме или через бота."
        })
    else:
        return render(request, "message.html", {
            "title": "👍 Данные подписки изменены",
            "message": ""
        })


def render_weekly_digest(request):
    try:
        digest, _ = generate_weekly_digest(no_footer=True)
    except NotFound:
        raise Http404()

    return HttpResponse(digest)


@api(require_auth=True)
def link_telegram(request):
    if not request.body:
        raise Http404()

    if request.method == "POST":
        data = json.loads(request.body)
        if not data.get("id") or not data.get("hash"):
            return render(request, "error.html", {
                "title": "Что-то пошло не так",
                "message": "Попробуйте авторизоваться снова.",
            }, status=400)

        if not is_valid_telegram_data(data, settings.TELEGRAM_TOKEN):
            raise AccessDenied(title="Подпись сообщения не совпадает")

        request.me.telegram_id = data["id"]
        request.me.telegram_data = data
        request.me.save()

        cache.delete("bot:telegram_user_ids")

        full_name = str(request.me.telegram_data.get("first_name") or "") \
            + str(request.me.telegram_data.get("last_name") or "")

        return {
            "status": "success",
            "telegram": {
                "id": request.me.telegram_id,
                "username": request.me.telegram_data.get("username") or full_name,
                "full_name": full_name,
            }
        }

    return {"status": "nope"}


def is_valid_telegram_data(data, bot_token):
    data = dict(data)
    check_hash = data.pop('hash')
    check_list = ['{}={}'.format(k, v) for k, v in data.items()]
    check_string = '\n'.join(sorted(check_list))

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    hmac_hash = hmac.new(
        secret_key,
        check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(hmac_hash, check_hash)
