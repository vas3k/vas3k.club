import mistune

LIST_BULLET_POINTS = {1: "• ", 2: "◦ ", 3: "▪ "}


def get_bullet_point(level: int) -> str:
    return LIST_BULLET_POINTS[(level - 1) % len(LIST_BULLET_POINTS) + 1]


def indent(level: int) -> str:
    return "  " * (level - 1)


def convert_bulet_to_ordered_list(text, level, start):
    current_indent = indent(level)
    prefix_to_change = f"{current_indent}{get_bullet_point(level)}"
    items = text.split("\n" + prefix_to_change)
    items[0] = items[0][len(prefix_to_change):]
    return "\n".join(f"{current_indent}{i}. {item}" for i, item in enumerate(items, start or 1))


class TelegramRenderer(mistune.HTMLRenderer):
    def image(self, src, alt="", title=None):
        if alt:
            return f'<a href="{src}">🏞 «{alt}»</a>'
        else:
            return f'<a href="{src}">🏞🔗</a>'

    def strikethrough(self, text):
        return f"<s>{text}</s>"

    def linebreak(self):
        return "\n"

    def paragraph(self, text):
        return text + "\n\n"

    def heading(self, text, level):
        return f"<b>{text}</b>\n\n"

    def newline(self):
        return "\n"

    def list(self, text, ordered, level, start=None):
        if ordered:
            text = convert_bulet_to_ordered_list(text, level, start)
        if level > 1:
            text = "\n" + text
        return text

    def list_item(self, text, level):
        return f"{indent(level)}{get_bullet_point(level)}{text}\n"

    def thematic_break(self):
        return '---\n'
