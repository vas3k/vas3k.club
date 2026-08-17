import ipaddress


def parse_ip_address(request):
    # SECURITY: X-Real-IP and the FIRST X-Forwarded-For entry are client-controlled and were
    # spoofable (view/vote antifraud bypass, IP-ban evasion). The rightmost XFF entry is the
    # one appended by our own nginx ($proxy_add_x_forwarded_for) and reflects the real peer.
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        ip = xff.split(",")[-1].strip()
    else:
        ip = request.environ.get("REMOTE_ADDR") or ""

    try:
        # Validate if it's a proper IP address
        ipaddress.ip_address(ip)
    except ValueError:
        ip = "0.0.0.0"

    return ip


def parse_useragent(request):
    return (request.META.get("HTTP_USER_AGENT") or "")[:512]
