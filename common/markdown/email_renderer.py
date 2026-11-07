import html

from mistune.util import striptags

from common.markdown.club_renderer import ClubRenderer
from common.regexp import YOUTUBE_RE


class EmailRenderer(ClubRenderer):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def simple_image(self, url, text="", title=None):
        alt = html.escape(html.unescape(striptags(text)))
        return f"""<img src="{html.escape(url)}" alt="{alt}" width="600" border="0"><br>{html.escape(title or "")}"""

    def youtube(self, url, text="", title=None):
        youtube_match = YOUTUBE_RE.match(url)
        youtube_id = html.escape(youtube_match.group(1) or "")
        return f'<a href="{html.escape(url)}"><span class="ratio-16-9 video-preview" ' \
               f'style="background-image: url(\'https://img.youtube.com/vi/{html.escape(youtube_id)}/0.jpg\');">' \
               f'</span></a><br>{html.escape(title or "")}'

    def video(self, url, text="", title=None):
        fallback = html.escape(html.unescape(striptags(text)))
        return f'<video src="{html.escape(url)}" controls muted playsinline>{fallback}</video><br>{html.escape(title or "")}'

    def tweet(self, url, text="", title=None):
        return f'<a href="{html.escape(url)}">{html.escape(url)}</a><br>{html.escape(title or "")}'

    def heading(self, text, level, **attrs):
        tag = f"h{level}"
        return f"<{tag}>{text}</{tag}>\n"
