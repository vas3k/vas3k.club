from django import forms
from django.template.loader import render_to_string

from godmode.models import ClubSettings


class WeeklyDigestComposeForm(forms.ModelForm):
    digest_title = forms.CharField(
        label="Заголовок следующего дайджеста",
        required=False,
        max_length=200,
    )

    digest_intro = forms.CharField(
        label="Интро к следующему дайджесту",
        required=False,
        max_length=10000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 50000,
                "class": "markdown-editor-full",
            }
        ),
    )

    class Meta:
        model = ClubSettings
        fields = [
            "digest_title",
            "digest_intro",
        ]


def compose_weekly_digest(request, admin_page):
    god_settings = ClubSettings.objects.first()

    if request.method == "POST":
        form = WeeklyDigestComposeForm(request.POST, request.FILES, instance=god_settings)
        if form.is_valid():
            form.save()
            return render_to_string("godmode/pages/message.html", {
                "title": "💌 Дайджест сохранен",
                "message": f"Он будет отправлен в понедельник утром по расписанию. "
                           f"До этого момента вы всегда можете его отредактировать.",
            }, request=request)
    else:
        form = WeeklyDigestComposeForm(instance=god_settings)

    return render_to_string("godmode/pages/simple_form.html", {
        "form": form
    }, request=request)
