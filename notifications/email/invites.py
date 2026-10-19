from django.template import loader

from invites.models import Invite
from notifications.email.sender import send_transactional_email
from users.models.user import User


def send_invite_purchase_confirmation(from_user: User, invite: Invite):
    invite_template = loader.get_template("notifications/emails/invite_confirm.html")
    send_transactional_email(
        recipient=from_user.email,
        subject=f"🎁 Вы купили инвайт",
        html=invite_template.render({"from_user": from_user, "invite": invite}),
        tags=["invited"]
    )


def send_invited_email(from_user: User, to_user: User):
    invite_template = loader.get_template("notifications/emails/invited.html")
    send_transactional_email(
        recipient=to_user.email,
        subject=f"🚀 Вас пригласили в Клуб",
        html=invite_template.render({"from_user": from_user, "to_user": to_user}),
        tags=["invited"]
    )


def send_account_renewed_email(from_user: User, to_user: User):
    invite_template = loader.get_template("notifications/emails/invite_renewed.html")
    send_transactional_email(
        recipient=to_user.email,
        subject=f"🚀 Вам оплатили аккаунт в Клубе",
        html=invite_template.render({"from_user": from_user, "to_user": to_user}),
        tags=["invited"]
    )
