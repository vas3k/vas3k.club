from django import forms

from godmode.models import ClubSettings
from users.models.achievements import Achievement


class GodmodeDigestEditForm(forms.ModelForm):
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


class GodmodeInviteForm(forms.Form):
    email = forms.EmailField(
        label="E-mail",
        required=True,
    )

    days = forms.IntegerField(
        label="Дней",
        required=True,
        initial=365,
    )


class GodmodeMassEmailForm(forms.Form):
    email_title = forms.CharField(
        label="Заголовок",
        required=True,
        max_length=128,
    )

    email_text = forms.CharField(
        label="Текст письма в Markdown",
        required=True,
        max_length=10000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 50000,
                "class": "markdown-editor-full",
            }
        ),
    )

    recipients = forms.CharField(
        label="Получатели: имейлы или ники в Клубе через запятую",
        required=True,
        max_length=10000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 50000,
                "placeholder": "vas3k,pivas3k,me@vas3k.ru",
            }
        ),
    )

    is_promo = forms.BooleanField(
        label="Это промо?",
        required=False,
    )


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
