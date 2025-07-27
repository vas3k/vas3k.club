from notifications.telegram.common import send_telegram_image, render_html_message, send_telegram_message, Chat
from users.models.achievements import UserAchievement


def send_new_achievement_notification(user_achievement: UserAchievement):
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
