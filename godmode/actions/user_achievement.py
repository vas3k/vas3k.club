from django import forms
from django.shortcuts import render

from common.data.achievements import ACHIEVEMENTS
from notifications.email.achievements import send_new_achievement_email
from notifications.telegram.achievements import notify_user_new_achievement, notify_admins_on_achievement
from users.models.achievements import Achievement, UserAchievement
from users.models.user import User


class UserAchievementForm(forms.Form):
    new_achievement = forms.ChoiceField(
        label="Выдать новую ачивку",
        choices=[(None, "---")] + [(key, value.get("name")) for key, value in ACHIEVEMENTS],
        required=True,
    )


def get_achievement_action(request, user: User, **context):
    return render(request, "godmode/action.html", {
        **context,
        "item": user,
        "form": UserAchievementForm(),
    })


def post_achievement_action(request, user: User, **context):
    form = UserAchievementForm(request.POST, request.FILES)
    if form.is_valid():
        data = form.cleaned_data

        # Achievements
        if data["new_achievement"]:
            achievement = Achievement.objects.filter(code=data["new_achievement"]).first()
            if achievement:
                user_achievement, is_created = UserAchievement.objects.get_or_create(
                    user=user,
                    achievement=achievement,
                )
                if is_created:
                    send_new_achievement_email(user_achievement)
                    notify_user_new_achievement(user_achievement)
                    notify_admins_on_achievement(user_achievement, from_user=request.me)

        return render(request, "godmode/message.html", {
            **context,
            "title": f"Юзер {user.full_name} получил ачивку {achievement.name}",
            "message": f"Ура 🎉",
        })
    else:
        return render(request, "godmode/action.html", {
            **context,
            "item": user,
            "form": form,
        })

