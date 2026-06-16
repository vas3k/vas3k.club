from django import forms
from django.shortcuts import render

from common.data.ban import TEMPORARY_BAN_REASONS, PERMANENT_BAN_REASONS, BanReason
from users.helpers import unban_user, temporary_ban_user, custom_ban_user, permanently_ban_user
from users.models.user import User


class UserBanForm(forms.Form):
    is_temporarily_banned = forms.BooleanField(
        label="Забанить временно",
        required=False
    )

    temporary_ban_reason = forms.ChoiceField(
        label="Причина",
        choices=[(key, f"{reason.name} ({reason.min_duration}+ дней)") for key, reason in TEMPORARY_BAN_REASONS.items()],
        required=False,
    )

    is_permanently_banned = forms.BooleanField(
        label="Забанить навечно",
        required=False
    )

    permanent_ban_reason = forms.ChoiceField(
        label="Причина",
        choices=[(key, reason.name) for key, reason in PERMANENT_BAN_REASONS.items()],
        required=False,
    )

    is_custom_banned = forms.BooleanField(
        label="Забанить кастомно",
        required=False
    )

    custom_ban_days = forms.IntegerField(
        label="Бан истечет через N дней",
        initial=5,
        required=False
    )

    custom_ban_name = forms.CharField(
        label="Короткая причина",
        max_length=80,
        required=False,
    )

    custom_ban_reason = forms.CharField(
        label="Развернутый комментарий и ссылки (опционально)",
        max_length=5000,
        required=False,
        widget=forms.Textarea(attrs={"maxlength": 5000}),
    )

    is_unbanned = forms.BooleanField(
        label="Разбанить",
        required=False
    )


def get_ban_action(request, user: User, **context):
    return render(request, "godmode/actions/user_ban.html", {
        **context,
        "item": user,
        "form": UserBanForm(),
    })


def post_ban_action(request, user: User, **context):
    form = UserBanForm(request.POST, request.FILES)
    if form.is_valid():
        data = form.cleaned_data

        # Unban
        if data["is_unbanned"]:
            unban_user(user)
            return render(request, "godmode/message.html", {
                **context,
                "title": f"Юзер {user.full_name} разбанен",
                "message": f"Снова может щитпостить",
            })

        is_banned = False

        # Temporary ban
        if data["is_temporarily_banned"]:
            reason = TEMPORARY_BAN_REASONS.get(data["temporary_ban_reason"])
            is_banned = temporary_ban_user(
                user=user,
                reason=reason
            )

        # Custom ban
        if data["is_custom_banned"]:
            is_banned = custom_ban_user(
                user=user,
                days=data["custom_ban_days"],
                reason=BanReason(name=data["custom_ban_name"], description=data["custom_ban_reason"],
                                 min_duration=data["custom_ban_days"])
            )

        # Permanent ban
        if data["is_permanently_banned"]:
            reason = PERMANENT_BAN_REASONS.get(data["permanent_ban_reason"])
            is_banned = permanently_ban_user(
                user=user,
                reason=reason
            )

        return render(request, "godmode/message.html", {
            **context,
            "title": f"Юзер {user.full_name} забанен" if is_banned else "Ошибка",
            "message": f"Ура 🎉" if is_banned else "😭 Вы забыли поставить галочку или случилась какая-то ошибка",
        })
    else:
        return render(request, "godmode/actions/user_ban.html", {
            **context,
            "item": user,
            "form": form,
        })

