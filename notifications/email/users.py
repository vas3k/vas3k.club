from django.template import loader, TemplateDoesNotExist

from auth.models import Code
from bot.common import RejectReason
from notifications.email.sender import send_club_email
from users.models.user import User


def send_welcome_drink(user: User):
    welcome_drink_template = loader.get_template("emails/welcome.html")
    send_club_email(
        recipient=user.email,
        subject=f"Велком дринк 🍸",
        html=welcome_drink_template.render({"user": user}),
        tags=["welcome"]
    )


def send_rejected_email(user: User, reason: RejectReason):
    try:
        rejected_template = loader.get_template(f"emails/rejected/{reason.value}.html")
    except TemplateDoesNotExist:
        rejected_template = loader.get_template(f"emails/rejected/intro.html")

    send_club_email(
        recipient=user.email,
        subject=f"😕 Пока нет",
        html=rejected_template.render({"user": user}),
        tags=["rejected"]
    )


def send_auth_email(user: User, code: Code):
    auth_template = loader.get_template("emails/auth.html")
    send_club_email(
        recipient=user.email,
        subject=f"{code.code} — ваш код для входа",
        html=auth_template.render({"user": user, "code": code}),
        tags=["auth"]
    )


def send_unmoderated_email(user: User):
    rejected_template = loader.get_template("emails/unmoderated.html")
    send_club_email(
        recipient=user.email,
        subject=f"😱 Вас размодерировали",
        html=rejected_template.render({"user": user}),
        tags=["unmoderated"]
    )


def send_banned_email(user: User, days: int, reason: str):
    if not user.is_banned or not days:
        return  # not banned oO

    rejected_template = loader.get_template("emails/banned.html")
    send_club_email(
        recipient=user.email,
        subject=f"💩 Вас забанили",
        html=rejected_template.render({
            "user": user,
            "days": days,
            "reason": reason,
        }),
        tags=["banned"]
    )


def send_ping_email(user: User, message: str):
    rejected_template = loader.get_template("emails/ping.html")
    send_club_email(
        recipient=user.email,
        subject=f"👋 Вам письмо",
        html=rejected_template.render({"message": message}),
        tags=["ping"]
    )


def send_data_archive_ready_email(user, url):
    auth_template = loader.get_template("emails/data_archive_ready.html")
    send_club_email(
        recipient=user.email,
        subject=f"Ваш архив с данными сгенерировался",
        html=auth_template.render({"user": user, "url": url}),
        tags=["gdpr"]
    )
