import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, Http404
from django.shortcuts import render
from telegram import Update

from auth.helpers import auth_required
from bot.bot import bot
from bot.handlers.moderator import process_moderator_actions
from bot.handlers.personal import process_personal_chat_updates, process_auth
from bot.handlers.replies import process_comment_reply
from club.exceptions import AccessDenied
from common.request import ajax_request
from users.models.user import User

log = logging.getLogger(__name__)


def webhook_telegram(request, token):
    if not bot:
        return HttpResponse("Not configured", status=500)

    if token != settings.TELEGRAM_TOKEN:
        return HttpResponse("Go away", status=400)

    # try to get the json body or poll the latest updates
    if request.body:
        updates = [Update.de_json(json.loads(request.body), bot)]
    else:
        # useful in development
        updates = bot.get_updates()

    for update in updates:
        log.info(f"Update: {update.to_dict()}")

        if update.effective_chat:
            # admin chat
            if str(update.effective_chat.id) == settings.TELEGRAM_ADMIN_CHAT_ID:
                if update.callback_query:
                    process_moderator_actions(update)

            # reply to a comment (in any chat excluding admin)
            elif update.message and update.message.reply_to_message \
                    and update.message.reply_to_message.text \
                    and update.message.reply_to_message.text.startswith("💬"):
                if is_club_user(update.effective_user.id):
                    process_comment_reply(update)

            # personal chats with users
            elif update.effective_user and update.effective_chat.id == update.effective_user.id:
                if is_club_user(update.effective_user.id):
                    process_personal_chat_updates(update)
                else:
                    process_auth(update)  # new user?

    return HttpResponse("OK")


def is_club_user(telegram_user_id):
    club_users = cache.get("bot:telegram_user_ids")
    if not club_users:
        club_users = User.objects\
            .filter(telegram_id__isnull=False, moderation_status=User.MODERATION_STATUS_APPROVED)\
            .values_list("telegram_id", flat=True)
        cache.set("bot:telegram_user_ids", list(club_users), 5 * 60)
    return str(telegram_user_id) in set(club_users)


@auth_required
@ajax_request
def link_telegram(request):
    if not request.body:
        raise Http404()

    if request.method == "POST":
        data = json.loads(request.body)
        if not data.get("id") or not data.get("hash"):
            return render(request, "error.html", {
                "title": "Что-то пошло не так",
                "message": "Попробуйте авторизоваться снова.",
            })

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

    return hmac_hash == check_hash
