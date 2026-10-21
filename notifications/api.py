import hashlib
import hmac

from django.conf import settings
from django.core.cache import cache
from django.views.decorators.http import require_http_methods

from authn.decorators.api import api
from club.exceptions import AccessDenied, ApiBadRequest
from common.api import API


@api(require_auth=True)
@require_http_methods(["POST"])
def link_telegram(request):
    data = API.parse_body(request)

    if not data.get("id") or not isinstance(data.get("hash"), str) or not data["hash"]:
        raise ApiBadRequest(
            title="Что-то пошло не так",
            message="Попробуйте авторизоваться снова.",
        )

    if not is_valid_telegram_data(data, settings.TELEGRAM_TOKEN):
        raise AccessDenied(title="Подпись сообщения не совпадает")

    request.me.telegram_id = data["id"]
    request.me.telegram_data = data
    request.me.save()

    cache.delete("bot:telegram_user_ids")

    full_name = str(data.get("first_name") or "") + str(data.get("last_name") or "")

    return {
        "status": "success",
        "telegram": {
            "id": request.me.telegram_id,
            "username": data.get("username") or full_name,
            "full_name": full_name,
        }
    }


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
