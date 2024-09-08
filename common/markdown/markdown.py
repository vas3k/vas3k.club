import mistune

from common.markdown.club_renderer import ClubRenderer
from common.markdown.email_renderer import EmailRenderer
from common.markdown.plain_renderer import PlainRenderer
from common.markdown.telegram_renderer import TelegramRenderer


def markdown_text(text, renderer=ClubRenderer):
    markdown = mistune.create_markdown(
        escape=True, renderer=renderer(), plugins=["strikethrough", "url"]
    )
    return (markdown(text) or "").strip()


def markdown_plain(text):
    return markdown_text(text, renderer=PlainRenderer)


def markdown_tg(text):
    return markdown_text(text, renderer=TelegramRenderer)


def markdown_email(text):
    return markdown_text(text, renderer=EmailRenderer)
