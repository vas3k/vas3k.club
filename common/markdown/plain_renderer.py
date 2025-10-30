import mistune


class PlainRenderer(mistune.HTMLRenderer):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def link(self, text, url, title=None):
        if text:
            return f'[{text}]({url})'
        else:
            return f'({url})'

    def image(self, text, url, title=None):
        return "🖼"

    def emphasis(self, text):
        return text

    def strong(self, text):
        return text

    def codespan(self, text):
        return text

    def linebreak(self):
        return "\n"

    def paragraph(self, text):
        return text + "\n\n"

    def heading(self, text, level, **attrs):
        return text + "\n\n"

    def newline(self):
        return "\n"

    def block_quote(self, text):
        return "> " + text

    def block_code(self, code, info=None):
        return code

    def list(self, text, ordered, **attrs):
        return text

    def list_item(self, text):
        return f"- {text}\n"

    def thematic_break(self):
        return '---\n'
