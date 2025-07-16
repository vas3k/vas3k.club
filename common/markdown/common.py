from mistune import escape_html


def split_title_and_css_classes(value) -> [str, list]:
    if value.startswith("."):
        try:
            classes, title = value.split(" ", 1)
        except ValueError:
            classes, title = value, ""
        return title, [c for c in escape_html(classes).split(".") if c.strip()]
    return value, []
