from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from common.markdown.markdown import markdown_email, markdown_tg


def render_message(path: str, context: dict | None = None) -> str:
    return render_to_string(f"messages/{path}", context or {}).strip()


def render_message_for_telegram(path: str, context: dict | None = None) -> str:
    return markdown_tg(render_message(path, context))


def render_message_for_email(path: str, title: str, context: dict | None = None) -> str:
    body_html = mark_safe(markdown_email(render_message(path, context)))
    return render_to_string("notifications/emails/markdown_message.html", {
        "title": title,
        "body": body_html,
    })
