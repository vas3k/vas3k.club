from django.template import loader

from notifications.email.sender import send_club_email
from users.models.user import User


def send_invited_email(from_user: User, to_user: User):
    invite_template = loader.get_template("emails/invited.html")
    send_club_email(
        recipient=to_user.email,
        subject=f"🚀 Вас пригласили в Клуб",
        html=invite_template.render({"from_user": from_user, "to_user": to_user}),
        tags=["invited"]
    )


def send_invite_confirmation(from_user: User, to_user: User):
    invite_template = loader.get_template("emails/invite_confirm.html")
    send_club_email(
        recipient=from_user.email,
        subject=f"👍 Вы пригласили '{to_user.email}' в Клуб",
        html=invite_template.render({"from_user": from_user, "to_user": to_user}),
        tags=["invited"]
    )
