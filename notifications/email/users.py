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
