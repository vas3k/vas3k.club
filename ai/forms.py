from django import forms


class LlmAgentForm(forms.Form):
    input = forms.CharField(
        label="Запрос",
        required=True,
        max_length=1000,
    )
