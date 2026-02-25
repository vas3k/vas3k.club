import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = ("http", "https")


def is_url_safe_for_fetch(url: str) -> bool:
    """Check if URL is safe for server-side fetching (resolves to a public address)."""
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    try:
        addr_info = socket.getaddrinfo(hostname, None)
        return all(
            ipaddress.ip_address(sockaddr[0]).is_global
            for _family, _type, _proto, _canonname, sockaddr in addr_info
        )
    except (socket.gaierror, ValueError):
        return False
