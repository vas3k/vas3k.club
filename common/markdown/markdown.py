import mistune

from common.markdown.club_renderer import ClubRenderer, ClubInlineParser
from common.markdown.email_renderer import EmailRenderer
from common.markdown.plain_renderer import PlainRenderer


def markdown_text(text, renderer=ClubRenderer):
    renderer_obj = renderer()

    def _set_club_inline(self):
        self.inline = ClubInlineParser(renderer_obj)

    plugins = ["strikethrough", "url"]
    if renderer == ClubRenderer:
        plugins.append(_set_club_inline)

    markdown = mistune.create_markdown(
        escape=True, renderer=renderer_obj, plugins=plugins
    )

    return (markdown(text) or "").strip()


def markdown_plain(text):
    return markdown_text(text, renderer=PlainRenderer)


def markdown_email(text):
    return markdown_text(text, renderer=EmailRenderer)
