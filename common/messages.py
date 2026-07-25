from pathlib import Path

from django.conf import settings
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from common.markdown.markdown import markdown_email, markdown_tg

MESSAGES_ROOT = Path(settings.BASE_DIR) / "frontend" / "messages"


def render_message(path: str, context: dict | None = None) -> str:
    """Render a Django-templated markdown file from frontend/messages/."""
    message_path = MESSAGES_ROOT / path
    template = Template(message_path.read_text(encoding="utf-8"))
    return template.render(Context(context or {})).strip()


def render_message_for_telegram(path: str, context: dict | None = None) -> str:
    return markdown_tg(render_message(path, context))


def render_message_for_email(path: str, title: str, context: dict | None = None) -> str:
    body_html = mark_safe(markdown_email(render_message(path, context)))
    return render_to_string("emails/markdown_message.html", {
        "title": title,
        "body": body_html,
    })
