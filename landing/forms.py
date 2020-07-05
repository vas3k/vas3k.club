from django import forms

from landing.models import GodSettings


class GodSettingsEditForm(forms.ModelForm):
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
            "digest_intro",
            "network_page",
        ]
