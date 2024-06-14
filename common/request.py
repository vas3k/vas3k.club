def parse_ip_address(request):
    ipaddress = request.META.get("HTTP_X_REAL_IP") \
        or request.META.get("HTTP_X_FORWARDED_FOR") \
        or request.environ.get("REMOTE_ADDR") or ""

    if "," in ipaddress:  # multiple ips in the header
        ipaddress = ipaddress.split(",", 1)[0]

    if "." not in ipaddress:  # malformed ip, maybe vpn
        ipaddress = "0.0.0.0"

    return ipaddress


def parse_useragent(request):
    return (request.META.get("HTTP_USER_AGENT") or "")[:512]
