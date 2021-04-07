import logging
import re

from django.conf import settings
from django.core.mail import send_mail
from premailer import Premailer

log = logging.getLogger(__name__)


def send_club_email(recipient, subject, html, tags=None):
    log.info(f"Sending email to {recipient}")
    prepared_html = prepare_letter(html, base_url=settings.APP_HOST)
    return send_mail(
        subject=subject,
        html_message=prepared_html,
        message=re.sub(r"<[^>]+>", "", prepared_html),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
    )


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
