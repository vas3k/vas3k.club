import logging
from collections import namedtuple
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from common.url_security import is_url_safe_for_fetch
from django.utils.html import strip_tags
from requests import RequestException
from urllib3.exceptions import InsecureRequestWarning

DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 "
                  "Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
}
DEFAULT_REQUEST_TIMEOUT = 10
MAX_PARSABLE_CONTENT_LENGTH = 15 * 1024 * 1024  # 15Mb

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
log = logging.getLogger(__name__)


ParsedURL = namedtuple("ParsedURL", ["url", "domain", "title", "favicon", "summary", "image", "description"])


def parse_url_preview(url: str) -> Optional[ParsedURL]:
    real_url, content_type, content_length = resolve_url(url)

    # do not parse non-text content
    if not content_type or not content_type.startswith("text/"):
        return None

    html = load_page_safe(real_url)
    if not html:
        return None

    parsed = parse_html_preview(real_url, html)
    if not parsed:
        return None

    return parsed


def parse_html_preview(url: str, html: str | bytes) -> Optional[ParsedURL]:
    soup = BeautifulSoup(html, "html.parser")

    canonical = _meta_link(soup, rel="canonical") or url
    title = (
        _meta_content(soup, property="og:title")
        or _meta_content(soup, name="twitter:title")
        or (soup.title.string if soup.title and soup.title.string else None)
        or ""
    )
    description = (
        _meta_content(soup, property="og:description")
        or _meta_content(soup, name="twitter:description")
        or _meta_content(soup, name="description")
        or ""
    )
    image = (
        _meta_content(soup, property="og:image")
        or _meta_content(soup, name="twitter:image")
        or ""
    )
    favicon = (
        _meta_link(soup, rel="icon")
        or _meta_link(soup, rel="shortcut icon")
        or _meta_link(soup, rel="apple-touch-icon")
        or ""
    )

    if image:
        image = urljoin(canonical, image)
    if favicon:
        favicon = urljoin(canonical, favicon)

    return ParsedURL(
        url=canonical,
        domain=urlparse(canonical).netloc,
        title=strip_tags(title).strip(),
        favicon=strip_tags(favicon),
        summary="",
        image=image,
        description=strip_tags(description).strip(),
    )


def _meta_content(soup: BeautifulSoup, **attrs) -> Optional[str]:
    tag = soup.find("meta", attrs=attrs)
    if not tag:
        return None
    content = tag.get("content")
    return content.strip() if content else None


def _meta_link(soup: BeautifulSoup, rel: str) -> Optional[str]:
    wanted = rel.lower()

    def matches(value) -> bool:
        if not value:
            return False
        tokens = value if isinstance(value, list) else value.split()
        return wanted in {token.lower() for token in tokens}

    tag = soup.find("link", rel=matches)
    if not tag:
        return None
    href = tag.get("href")
    return href.strip() if href else None


def resolve_url(entry_link: str) -> Tuple[Optional[str], Optional[str], int]:
    url = str(entry_link)
    content_type = None
    content_length = MAX_PARSABLE_CONTENT_LENGTH + 1  # don't parse null content-types

    for _ in range(10):
        if not is_url_safe_for_fetch(url):
            log.warning(f"Blocked URL: {url}")
            return None, content_type, content_length

        try:
            response = requests.head(
                url, timeout=DEFAULT_REQUEST_TIMEOUT,
                verify=False, stream=True,
                allow_redirects=False,
            )
        except RequestException:
            log.warning(f"Failed to resolve URL: {url}")
            return None, content_type, content_length

        if 300 <= response.status_code < 400:
            redirect_url = response.headers.get("location", "")
            if not urlparse(redirect_url).netloc:
                redirect_url = urljoin(url, redirect_url)
            url = redirect_url
        else:
            content_type = response.headers.get("content-type")
            content_length = int(response.headers.get("content-length") or 0)
            return url, content_type, content_length

    return None, content_type, content_length


def load_page_safe(url: str) -> str:
    if not is_url_safe_for_fetch(url):
        log.warning(f"Blocked page URL: {url}")
        return ""

    try:
        response = requests.get(
            url=url,
            timeout=DEFAULT_REQUEST_TIMEOUT,
            headers=DEFAULT_REQUEST_HEADERS,
            stream=True,  # the most important part — stream response to prevent loading everything into memory
            allow_redirects=False,
        )
    except RequestException as ex:
        log.warning(f"Error parsing the page: {url} {ex}")
        return ""
    # https://stackoverflow.com/a/23514616
    return response.raw.read(MAX_PARSABLE_CONTENT_LENGTH, decode_content=True)
