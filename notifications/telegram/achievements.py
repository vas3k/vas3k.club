from django.conf import settings
from django.urls import reverse

from notifications.telegram.common import send_telegram_image, render_html_message, send_telegram_message, Chat, \
    VIBES_CHAT
from users.models.achievements import UserAchievement
from users.models.user import User


def notify_user_new_achievement(user_achievement: UserAchievement):
    if user_achievement.user.is_member and user_achievement.user.telegram_id:
        if user_achievement.achievement.image:
            send_telegram_image(
                chat=Chat(id=user_achievement.user.telegram_id),
                image_url=user_achievement.achievement.image,
                text=render_html_message(
                    "achievement.html",
                    user=user_achievement.user,
                    achievement=user_achievement.achievement
                ),
            )

        if user_achievement.achievement.custom_message:
            send_telegram_message(
                chat=Chat(id=user_achievement.user.telegram_id),
                text=user_achievement.achievement.custom_message,
            )


def notify_admins_on_achievement(user_achievement: UserAchievement, from_user: User = None):
    user_profile_url = settings.APP_HOST + reverse("profile", kwargs={"user_slug": user_achievement.user.slug})
    text = f"🏆 Юзеру <b><a href=\"{user_profile_url}\">{user_achievement.user.full_name}</a></b> " \
        f"дали ачивку «{user_achievement.achievement.name} (выдал: {from_user.full_name if from_user else None})»"

    for chat in [VIBES_CHAT]:
        send_telegram_message(chat=chat, text=text)
