import base64
import logging

from django.conf import settings
from django.db.models import Q
from django.template import loader

from notifications.email.sender import send_mass_email, send_transactional_email
from notifications.telegram.common import send_telegram_message, Chat
from users.models.user import User

log = logging.getLogger(__name__)


def send_custom_mass_email(emails_or_slugs: list[str], title: str, text: str, is_promo: bool = False):
    users = User.objects.filter(Q(slug__in=emails_or_slugs) | Q(email__in=emails_or_slugs)).all()
    if not text or not title:
        log.info("No text or title provided. Aborted")
        return False

    non_club_users = set(emails_or_slugs) - {user.email for user in users} - {user.slug for user in users}
    email_template = loader.get_template("emails/custom_markdown.html")

    # send emails to existing users
    for user in users:
        log.info(f"Sending email to {user.email}...")

        if is_promo and user.is_email_unsubscribed:
            log.info(f"User {user.email} is unsubscribed from promo emails. Skipping.")
            continue

        secret_code = base64.b64encode(user.secret_hash.encode("utf-8")).decode()
        sender = send_mass_email if is_promo else send_transactional_email
        sender(
            recipient=user.email,
            subject=title,
            html=email_template.render({
                "user": user,
                "title": title,
                "body": text,
            }),
            unsubscribe_link=f"{settings.APP_HOST}/notifications/unsubscribe/{user.id}/{secret_code}/",
        )

        if user.telegram_id:
            log.info(f"Sending telegram message to {user.telegram_id}...")
            send_telegram_message(
                chat=Chat(id=user.telegram_id),
                text=f"<b>{title}</b>\n\n{text}" if title else text,
            )

    # send emails to non club users
    for email in non_club_users:
        if "@" in email:
            send_transactional_email(
                recipient=email,
                subject=title,
                html=email_template.render({
                    "title": title,
                    "body": text,
                }),
            )

    return True

