from django import forms
from django.template.loader import render_to_string

from godmode.models import ClubSettings


class WeeklyDigestComposeForm(forms.Form):
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


def compose_weekly_digest(request, admin_page):
    if request.method == "POST":
        form = WeeklyDigestComposeForm(request.POST, request.FILES)
        if form.is_valid():
            ClubSettings.set("digest_title", form.cleaned_data["digest_title"])
            ClubSettings.set("digest_intro", form.cleaned_data["digest_intro"])

            return render_to_string("godmode/pages/message.html", {
                "title": "💌 Дайджест сохранен",
                "message": "Он будет отправлен в понедельник утром по расписанию. "
                           "До этого момента вы всегда можете его отредактировать.",
            }, request=request)
    else:
        form = WeeklyDigestComposeForm(initial={
            "digest_title": ClubSettings.get("digest_title"),
            "digest_intro": ClubSettings.get("digest_intro"),
        })

    return render_to_string("godmode/pages/simple_form.html", {
        "form": form
    }, request=request)
