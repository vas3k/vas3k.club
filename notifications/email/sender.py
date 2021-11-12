import logging
import re
from time import sleep

import sentry_sdk
from django.conf import settings
from django.core.mail import send_mail
from premailer import Premailer

log = logging.getLogger(__name__)


def send_club_email(recipient, subject, html, tags=None):
    prepared_html = prepare_letter(html, base_url=settings.APP_HOST)

    for _ in range(5):
        log.info(f"Sending email to {recipient}")
        try:
            return send_mail(
                subject=subject,
                html_message=prepared_html,
                message=re.sub(r"<[^>]+>", "", prepared_html),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
            )
        except Exception as e:
            sentry_sdk.capture_exception(e)
            log.warning("Cannot send email: %s", e)

        sleep(2)

    raise


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
