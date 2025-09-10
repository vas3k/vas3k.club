import ipaddress


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
