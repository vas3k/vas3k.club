from django.conf import settings
from django.urls import reverse

from notifications.telegram.common import send_telegram_message, ADMIN_CHAT, VIBES_CHAT, Chat


def notify_user_ban(user, days, reason):
    if user.telegram_id:
        send_telegram_message(
            chat=Chat(id=user.telegram_id),
            text=f"⛔ <b>К сожалению, вы получили бан в Клубе на {days} дней</b>.\n\n"
                 f"<b>Причина:</b> {reason}"
        )


def notify_admins_on_ban(user, days, reason):
    banned_user_profile_url = settings.APP_HOST + reverse("profile", kwargs={"user_slug": user.slug})
    text = f"⛔️ <b>Юзер <a href=\"{banned_user_profile_url}\">{user.full_name}</a> " \
        f"({user.slug}) забанен на {days} дней</b>" \
        f"\n\nПричина: <i>{reason}</i>"

    for chat in [ADMIN_CHAT, VIBES_CHAT]:
        send_telegram_message(chat=chat, text=text)
