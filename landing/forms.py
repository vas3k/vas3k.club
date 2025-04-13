from django import forms

from landing.models import GodSettings


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
        model = GodSettings
        fields = [
            "digest_title",
            "digest_intro",
        ]


class GodmodeNetworkSettingsEditForm(forms.ModelForm):
    network_page = forms.CharField(
        label="Страница «Сеть»",
        required=False,
        max_length=100000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 100000,
            }
        ),
    )

    class Meta:
        model = GodSettings
        fields = [
            "network_page",
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
            }
        ),
    )

    is_promo = forms.BooleanField(
        label="Это промо?",
        required=False,
    )

