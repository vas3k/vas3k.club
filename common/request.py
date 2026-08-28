import ipaddress
import re


def parse_ip_address(request):
    ip = request.META.get("HTTP_X_REAL_IP") \
        or request.META.get("HTTP_X_FORWARDED_FOR") \
        or request.environ.get("REMOTE_ADDR") or ""

    if "," in ip:  # multiple ips in the header
        ip = ip.split(",", 1)[0]

    try:
        # Validate if it's a proper IP address
        ipaddress.ip_address(ip)
    except ValueError:
        ip = "0.0.0.0"

    return ip


def parse_useragent(request):
    return (request.META.get("HTTP_USER_AGENT") or "")[:512]


_BROWSER_PATTERNS = (
    (r"YaBrowser/(\d+)", "Yandex"),
    (r"Edg(?:e|A|iOS)?/(\d+)", "Edge"),
    (r"OPR/(\d+)", "Opera"),
    (r"SamsungBrowser/(\d+)", "Samsung Internet"),
    (r"Firefox/(\d+)", "Firefox"),
    (r"FxiOS/(\d+)", "Firefox"),
    (r"Chrome/(\d+)", "Chrome"),
    (r"CriOS/(\d+)", "Chrome"),
    (r"Version/(\d+).+Safari/", "Safari"),
)


def browser_from_useragent(useragent):
    if not useragent:
        return None
    if "Telegram" in useragent:
        return "Telegram"
    for pattern, name in _BROWSER_PATTERNS:
        match = re.search(pattern, useragent)
        if match:
            return f"{name} {match.group(1)}"
    return None
