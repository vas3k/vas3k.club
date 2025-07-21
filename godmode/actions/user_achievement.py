from django import forms
from django.shortcuts import render

from common.data.achievements import ACHIEVEMENTS
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
                UserAchievement.objects.get_or_create(
                    user=user,
                    achievement=achievement,
                )

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

