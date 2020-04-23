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

    class Meta:
        model = GodSettings
        fields = [
            "digest_intro",
        ]
