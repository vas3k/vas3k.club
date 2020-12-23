import logging

import requests
from django.conf import settings
from premailer import Premailer


def send_club_email(recipient, subject, html, tags):
    return requests.post(
        settings.MAILGUN_API_URI + "/messages",
        auth=("api", settings.MAILGUN_API_KEY),
        data={
            "from": settings.MAILGUN_EMAIL_FROM,
            "to": [recipient],
            "subject": subject,
            "html": prepare_letter(html, base_url=settings.APP_HOST),
            "tags": tags,
            "text": "",
        }
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
