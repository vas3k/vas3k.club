import mistune

from common.markdown.common import split_title_and_css_classes


class TelegramRenderer(mistune.HTMLRenderer):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def link(self, text, url, title=None):
        text, _ = split_title_and_css_classes(text or "")
        return super().link(text, url, title)

    def image(self, text, url, title=None):
        if text:
            return f'<a href="{url}">🏞 «{text}»</a>'
        else:
            return f'<a href="{url}">🏞🔗</a>'

    def strikethrough(self, text):
        return f"<s>{text}</s>"

    def linebreak(self):
        return "\n"

    def paragraph(self, text):
        return text + "\n\n"

    def heading(self, text, level, **attrs):
        return f"<b>{text}</b>\n\n"

    def newline(self):
        return "\n"

    def list(self, text, ordered, **attrs):
        return text

    def list_item(self, text):
        return f"- {text}\n"

    def thematic_break(self):
        return '---\n'
