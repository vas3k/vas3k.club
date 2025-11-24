import html

ALLOWED_CSS_CLASSES_IN_MARKDOWN = {
    "image-wide",
    "button",
    "button-small",
    "button-big",
    "button-red",
    "button-blue",
    "button-inverted",
    "block",
    "border",
}

def split_title_and_css_classes(value) -> tuple[str, list]:
    if value.startswith("."):
        try:
            classes, title = value.split(" ", 1)
        except ValueError:
            classes, title = value, ""
        return title, [
            c for c in html.escape(classes).split(".") if c.strip() and c.strip() in ALLOWED_CSS_CLASSES_IN_MARKDOWN
        ]
    return value, []


def normalize_url(url: str, default_scheme: str = "https") -> str:
    if not url:
        return ""

    url = url.strip()
    if not url:
        return ""

    # add scheme if missing
    if not url.startswith("#") and not url.startswith("/") and not url.startswith("mailto:") and "://" not in url:
        url = f"{default_scheme}://{url}"

    return url
