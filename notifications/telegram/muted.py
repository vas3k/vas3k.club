from django.conf import settings
from django.urls import reverse

from notifications.telegram.common import send_telegram_message, ADMIN_CHAT, VIBES_CHAT


def notify_admins_on_mute(user_from, user_to, comment):
    user_from_profile_url = settings.APP_HOST + reverse("profile", kwargs={"user_slug": user_from.slug})
    user_to_profile_url = settings.APP_HOST + reverse("profile", kwargs={"user_slug": user_to.slug})
    text = f"<b>Кого-то замьютили</b> 🤕" \
            f"\n\n<a href=\"{user_from_profile_url}\">{user_from.full_name}</a> ({user_from.slug}) считает, " \
            f"что <a href=\"{user_to_profile_url}\">{user_to.full_name}</a> ({user_to.slug}) не место в Клубе " \
            f"и замьютил его. \n\nВот почему: <i>{comment}</i>"

    for chat in [ADMIN_CHAT, VIBES_CHAT]:
        send_telegram_message(chat=chat, text=text)
