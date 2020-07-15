from django.template import loader

from notifications.email.sender import send_club_email


def send_welcome_drink(user):
    welcome_drink_template = loader.get_template("emails/welcome.html")
    send_club_email(
        recipient=user.email,
        subject=f"Велком дринк 🍸",
        html=welcome_drink_template.render({"user": user}),
        tags=["welcome"]
    )


def send_rejected_email(user):
    rejected_template = loader.get_template("emails/rejected.html")
    send_club_email(
        recipient=user.email,
        subject=f"😕 Пока нет",
        html=rejected_template.render({"user": user}),
        tags=["rejected"]
    )


def send_unmoderated_email(user):
    rejected_template = loader.get_template("emails/unmoderated.html")
    send_club_email(
        recipient=user.email,
        subject=f"😱 Вас размодерировали",
        html=rejected_template.render({"user": user}),
        tags=["unmoderated"]
    )


def send_banned_email(user, days, reason):
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


def send_ping_email(user, message):
    rejected_template = loader.get_template("emails/ping.html")
    send_club_email(
        recipient=user.email,
        subject=f"👋 Вам письмо",
        html=rejected_template.render({"message": message}),
        tags=["ping"]
    )
