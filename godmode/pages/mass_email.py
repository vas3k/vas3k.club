from django import forms
from django.template.loader import render_to_string
from django_q.tasks import async_task

from notifications.email.custom import send_custom_mass_email


class GodmodeMassEmailForm(forms.Form):
    email_title = forms.CharField(
        label="Заголовок",
        required=True,
        max_length=128,
    )

    email_text = forms.CharField(
        label="Текст сообщения в Markdown (будет отправлен по почте и в telegram)",
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


def mass_email(request, admin_page):
    if request.method == "POST":
        form = GodmodeMassEmailForm(request.POST, request.FILES)
        if form.is_valid():
            emails_or_slugs = [u.strip().lstrip("@") for u in form.cleaned_data["recipients"].strip().split(",") if u.strip()]
            async_task(
                send_custom_mass_email,
                emails_or_slugs=emails_or_slugs,
                title=form.cleaned_data["email_title"],
                text=form.cleaned_data["email_text"],
                is_promo=form.cleaned_data["is_promo"],
            )
            return render_to_string("godmode/pages/message.html", {
                "title": f"📧 Рассылка запущена на {len(emails_or_slugs)} получателей",
                "message": "Вот этим людям щас будет отправлено письмо:\n" + ", ".join(emails_or_slugs)
            }, request=request)

    else:
        form = GodmodeMassEmailForm()

    return render_to_string("godmode/pages/simple_form.html", {
        "form": form
    }, request=request)
