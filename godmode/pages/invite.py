from datetime import datetime, timedelta

from django import forms
from django.template.loader import render_to_string

from notifications.email.invites import send_invited_email, send_account_renewed_email
from notifications.telegram.common import send_telegram_message, ADMIN_CHAT
from users.models.user import User


class InviteByEmailForm(forms.Form):
    email = forms.EmailField(
        label="E-mail",
        required=True,
    )

    days = forms.IntegerField(
        label="Дней",
        required=True,
        initial=365,
    )


def invite_user_by_email(request, admin_page):
    if request.method == "POST":
        form = InviteByEmailForm(request.POST, request.FILES)
        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()
            days = form.cleaned_data["days"]
            now = datetime.utcnow()

            user = User.objects.filter(email=email).first()
            if user:
                # add days to existing user instead of overwriting
                user.membership_expires_at = max(
                    now + timedelta(days=days),
                    user.membership_expires_at + timedelta(days=days)
                )
                user.membership_platform_type = User.MEMBERSHIP_PLATFORM_DIRECT
                user.updated_at = now
                user.save()
            else:
                # create new user with that email
                user, is_created = User.objects.get_or_create(
                    email=email,
                    defaults=dict(
                        membership_platform_type=User.MEMBERSHIP_PLATFORM_DIRECT,
                        full_name=email[:email.find("@")],
                        membership_started_at=now,
                        membership_expires_at=now + timedelta(days=days),
                        created_at=now,
                        updated_at=now,
                        moderation_status=User.MODERATION_STATUS_INTRO,
                    ),
                )

            if user.moderation_status == User.MODERATION_STATUS_INTRO:
                send_invited_email(request.me, user)
                send_telegram_message(
                    chat=ADMIN_CHAT,
                    text=f"🎁 <b>Юзера '{email}' заинвайтили за донат</b>",
                )
            else:
                send_account_renewed_email(request.me, user)
                send_telegram_message(
                    chat=ADMIN_CHAT,
                    text=f"🎁 <b>Юзеру '{email}' продлили аккаунт за донат</b>",
                )

            return render_to_string("godmode/pages/message.html", {
                "title": "🎁 Юзер приглашен",
                "message": f"Сейчас он получит на почту '{email}' уведомление об этом. "
                           f"Ему будет нужно залогиниться по этой почте и заполнить интро."
            }, request=request)
    else:
        form = InviteByEmailForm()

    return render_to_string("godmode/pages/simple_form.html", {
        "form": form
    }, request=request)
