import html


def split_title_and_css_classes(value) -> [str, list]:
    if value.startswith("."):
        try:
            classes, title = value.split(" ", 1)
        except ValueError:
            classes, title = value, ""
        return title, [c for c in html.escape(classes).split(".") if c.strip()]
    return value, []


def url_normalize(url: str, default_scheme: str = "https") -> str:
    if not url:
        return ""

    url = url.strip()
    if not url:
        return ""

    # add scheme if missing
    if not url.startswith("#") and not url.startswith("/") and "://" not in url:
        url = f"{default_scheme}://{url}"

    return url
