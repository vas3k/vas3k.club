from django.template import loader

from badges.models import UserBadge
from notifications.email.sender import send_transactional_email


def send_new_badge_email(user_badge: UserBadge):
    if not user_badge.to_user.is_email_unsubscribed:
        email_template = loader.get_template("emails/badge.html")
        send_transactional_email(
            recipient=user_badge.to_user.email,
            subject=f"🏅 Вам подарили награду «{user_badge.badge.title}»",
            html=email_template.render({"user_badge": user_badge}),
            tags=["badge"]
        )
