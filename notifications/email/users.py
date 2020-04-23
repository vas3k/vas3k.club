from django.template import loader

from notifications.email.sender import send_club_email

welcome_drink_template = loader.get_template("emails/welcome_drink.html")


def send_welcome_drink(user):
    send_club_email(
        recipient=user.email,
        subject=f"Велком дринк 🍸",
        html=welcome_drink_template.render({"user": user}),
        tags=["welcome"]
    )
