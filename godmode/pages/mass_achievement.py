from django import forms
from django.template.loader import render_to_string
from django_q.tasks import async_task

from notifications.email.achievements import send_new_achievement_email
from notifications.telegram.achievements import send_new_achievement_notification
from users.models.achievements import Achievement, UserAchievement
from users.models.user import User


class GodmodeMassAchievementForm(forms.Form):
    achievement = forms.ModelChoiceField(
        label="Ачивка",
        queryset=Achievement.objects.filter(is_visible=True),
        empty_label="---",
    )

    recipients = forms.CharField(
        label="Получатели: ники в Клубе через запятую",
        required=True,
        max_length=10000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 50000,
                "placeholder": "vas3k,pivas3k,petrovich",
            }
        ),
    )


def mass_achievement(request, admin_page):
    if request.method == "POST":
        form = GodmodeMassAchievementForm(request.POST, request.FILES)
        if form.is_valid():
            slugs = form.cleaned_data["recipients"].strip().split(",")
            users = User.objects.filter(slug__in=slugs)
            for user in users:
                user_achievement, is_created = UserAchievement.objects.get_or_create(
                    user=user,
                    achievement=form.cleaned_data["achievement"],
                )
                if is_created:
                    async_task(send_new_achievement_email, user_achievement)
                    async_task(send_new_achievement_notification, user_achievement)

            some_user_not_found = len(slugs) != users.count()
            return render_to_string("godmode/pages/message.html", {
                "title": f"🏆 Ачивка '{form.cleaned_data['achievement'].name}' выдана {users.count()} юзерам",
                "message": "Вот эти юзеры не найдены в Клубе, возможно ошибка в нике: " + ", ".join(
                    list(set(slugs) - set([u.slug for u in users]))
                ) if some_user_not_found else "Все юзеры получили ачивки!"
            }, request=request)
    else:
        form = GodmodeMassAchievementForm()

    return render_to_string("godmode/pages/simple_form.html", {
        "form": form
    }, request=request)
