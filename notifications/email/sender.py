import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from premailer import Premailer

log = logging.getLogger(__name__)


def send_transactional_email(recipient, subject, html, unsubscribe_link=None, **kwargs):
    log.info(f"Sending transactional email to {recipient}")
    prepared_html = prepare_letter(html, base_url=settings.APP_HOST)
    headers = {"List-Unsubscribe": unsubscribe_link} if unsubscribe_link else {}
    email = EmailMultiAlternatives(
        subject=subject,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
        headers=headers,
    )
    email.attach_alternative(prepared_html, "text/html")
    email.content_subtype = "html"
    return email.send(fail_silently=False)


def send_mass_email(recipient, subject, html, unsubscribe_link):
    log.info(f"Sending mass email to {recipient}")
    prepared_html = prepare_letter(html, base_url=settings.APP_HOST)
    email = EmailMultiAlternatives(
        subject=subject,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
        headers={
            "List-Unsubscribe": unsubscribe_link
        }
    )
    email.attach_alternative(prepared_html, "text/html")
    email.content_subtype = "html"
    return email.send(fail_silently=True)


def prepare_letter(html, base_url):
    html = Premailer(
        html=html,
        base_url=base_url,
        strip_important=False,
        keep_style_tags=True,
        capitalize_float_margin=True,
        cssutils_logging_level=logging.CRITICAL,
    ).transform()
    if "<!doctype" not in html:
        html = f"<!doctype html>{html}"
    return html
