from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template import loader
from django_q.tasks import async_task

from badges.models import UserBadge
from notifications.telegram.common import Chat, render_html_message, send_telegram_image
from notifications.email.sender import send_transactional_email


@receiver(post_save, sender=UserBadge)
def create_or_update_badge(sender, instance, created, **kwargs):
    if not created:
        return  # skip updates

    async_task(async_create_or_update_badge, instance)


def async_create_or_update_badge(user_badge: UserBadge):
    to_user = user_badge.to_user

    # messages
    if to_user.is_member and to_user.telegram_id:
        send_telegram_image(
            chat=Chat(id=to_user.telegram_id),
            image_url=f"{settings.APP_HOST}/static/images/badges/big/{user_badge.badge.code}.png",
            text=render_html_message("badge.html", user_badge=user_badge),
        )

    # emails
    if not to_user.is_email_unsubscribed:
        email_template = loader.get_template("emails/badge.html")
        send_transactional_email(
            recipient=to_user.email,
            subject=f"🏅 Вам подарили награду «{user_badge.badge.title}»",
            html=email_template.render({"user_badge": user_badge}),
            tags=["badge"]
        )
