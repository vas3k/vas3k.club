from django import forms

from authn.models.openid import OAuth2App


class AppForm(forms.ModelForm):
    name = forms.CharField(
        label="Название приложения",
        required=True,
    )

    description = forms.CharField(
        label="Описание для пользователя",
        required=True,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
            }
        ),
    )

    website = forms.URLField(
        label="URL вашего сайта или бота",
        required=False,
    )

    redirect_uris = forms.CharField(
        label="Разрешенные Callback URL для OAuth (можно несколько через запятую)",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
            }
        ),
    )

    class Meta:
        model = OAuth2App
        fields = [
            "name",
            "description",
            "website",
            "redirect_uris",
        ]
