from django.conf import settings

from badges.models import UserBadge
from notifications.telegram.common import send_telegram_image, Chat, render_html_message


def send_new_badge_message(user_badge: UserBadge):
    if user_badge.to_user.is_member and user_badge.to_user.telegram_id:
        send_telegram_image(
            chat=Chat(id=user_badge.to_user.telegram_id),
            image_url=f"{settings.APP_HOST}/static/images/badges/big/{user_badge.badge.code}.png",
            text=render_html_message("badge.html", user_badge=user_badge),
        )
