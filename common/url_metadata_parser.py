import logging
from collections import namedtuple
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from django.utils.html import strip_tags
from newspaper import ArticleException, Config, Article
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

    try:
        article = load_and_parse_full_article_text_and_image(real_url)
    except ArticleException:
        return None

    canonical_url = article.canonical_link or real_url
    return ParsedURL(
        url=canonical_url,
        domain=urlparse(canonical_url).netloc,
        title=strip_tags(article.title),
        favicon=strip_tags(urljoin(article.url, article.meta_favicon)),
        summary="",
        image=article.top_image,
        description=article.meta_description,
    )


def resolve_url(entry_link):
    url = str(entry_link)
    content_type = None
    content_length = MAX_PARSABLE_CONTENT_LENGTH + 1  # don't parse null content-types
    depth = 10
    while depth > 0:
        depth -= 1

        try:
            response = requests.head(url, timeout=DEFAULT_REQUEST_TIMEOUT, verify=False, stream=True)
        except RequestException:
            log.warning(f"Failed to resolve URL: {url}")
            return None, content_type, content_length

        if 300 < response.status_code < 400:
            url = response.headers["location"]  # follow redirect
        else:
            content_type = response.headers.get("content-type")
            content_length = int(response.headers.get("content-length") or 0)
            break

    return url, content_type, content_length


def load_page_safe(url: str) -> str:
    try:
        response = requests.get(
            url=url,
            timeout=DEFAULT_REQUEST_TIMEOUT,
            headers=DEFAULT_REQUEST_HEADERS,
            stream=True  # the most important part — stream response to prevent loading everything into memory
        )
    except RequestException as ex:
        log.warning(f"Error parsing the page: {url} {ex}")
        return ""
    # https://stackoverflow.com/a/23514616
    return response.raw.read(MAX_PARSABLE_CONTENT_LENGTH, decode_content=True)


def load_and_parse_full_article_text_and_image(url: str) -> Article:
    config = Config()
    config.MAX_SUMMARY_SENT = 8

    article = Article(url, config=config)
    article.set_html(load_page_safe(url))  # safer than article.download()
    article.parse()

    return article
