from django.template import loader

from notifications.email.sender import send_transactional_email
from users.models.achievements import UserAchievement


def send_new_achievement_email(user_achievement: UserAchievement):
    if not user_achievement.user.is_email_unsubscribed:
        email_template = loader.get_template("emails/achievement.html")
        send_transactional_email(
            recipient=user_achievement.user.email,
            subject=f"🏆 Вы получили ачивку «{user_achievement.achievement.name}»",
            html=email_template.render({"user": user_achievement.user, "achievement": user_achievement.achievement}),
            tags=["achievement"]
        )
