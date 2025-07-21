from datetime import datetime, timedelta

from django import forms
from django.conf import settings
from django.shortcuts import render

from authn.models.session import Session
from notifications.email.users import send_delete_account_confirm_email
from notifications.telegram.common import send_telegram_message, ADMIN_CHAT
from payments.helpers import cancel_all_stripe_subscriptions
from users.models.user import User


class UserDeleteForm(forms.Form):
    delete_account = forms.BooleanField(
        label="Удалить аккаунт и обнулить подписку",
        required=False
    )


def get_delete_action(request, user: User, **context):
    return render(request, "godmode/action.html", {
        **context,
        "item": user,
        "form": UserDeleteForm(),
    })


def post_delete_action(request, user: User, **context):
    form = UserDeleteForm(request.POST, request.FILES)
    if form.is_valid():
        data = form.cleaned_data

        # Delete account
        if data["delete_account"] and request.me.is_god:
            user.membership_expires_at = datetime.utcnow()
            user.is_banned_until = datetime.utcnow() + timedelta(days=5000)

            # cancel recurring payments
            cancel_all_stripe_subscriptions(user.stripe_id)

            # mark user for deletion
            user.deleted_at = datetime.utcnow()
            user.save()

            # remove sessions
            Session.objects.filter(user=user).delete()

            # notify user
            send_delete_account_confirm_email(
                user=user,
            )

            # notify admins
            send_telegram_message(
                chat=ADMIN_CHAT,
                text=f"💀 Юзер был удален админами: {settings.APP_HOST}/user/{user.slug}/",
            )

        return render(request, "godmode/message.html", {
            **context,
            "title": f"Юзера {user.full_name} был удален",
            "message": f"Он получит сообщение на почту и в телеграм, а через 3 дня все его данные будут удалены.",
        })
    else:
        return render(request, "godmode/action.html", {
            **context,
            "item": user,
            "form": form,
        })

