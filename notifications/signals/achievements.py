from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template import loader
from django_q.tasks import async_task

from notifications.telegram.common import Chat, render_html_message, send_telegram_image
from notifications.email.sender import send_transactional_email
from users.models.achievements import UserAchievement


@receiver(post_save, sender=UserAchievement)
def create_or_update_achievement(sender, instance, created, **kwargs):
    if not created:
        return  # skip updates

    async_task(async_create_or_update_achievement, instance)


def async_create_or_update_achievement(user_achievement: UserAchievement):
    user = user_achievement.user
    achievement = user_achievement.achievement

    # messages
    if user.is_member and user.telegram_id:
        if achievement.image:
            send_telegram_image(
                chat=Chat(id=user.telegram_id),
                image_url=achievement.image,
                text=render_html_message("achievement.html", user=user, achievement=achievement),
            )

    # emails
    if not user.is_email_unsubscribed:
        email_template = loader.get_template("emails/achievement.html")
        send_transactional_email(
            recipient=user.email,
            subject=f"🏆 Вы получили ачивку «{achievement.name}»",
            html=email_template.render({"user": user, "achievement": achievement}),
            tags=["achievement"]
        )
