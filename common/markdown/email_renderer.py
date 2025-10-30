import html

from common.markdown.club_renderer import ClubRenderer
from common.regexp import YOUTUBE_RE


class EmailRenderer(ClubRenderer):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def simple_image(self, src, alt="", title=None):
        return f"""<img src="{src}" alt="{alt}" width="600" border="0"><br>{title or ""}"""

    def youtube(self, src, alt="", title=None):
        youtube_match = YOUTUBE_RE.match(src)
        youtube_id = html.escape(youtube_match.group(1) or "")
        return f'<a href="{html.escape(src)}"><span class="ratio-16-9 video-preview" ' \
               f'style="background-image: url(\'https://img.youtube.com/vi/{html.escape(youtube_id)}/0.jpg\');">' \
               f'</span></a><br>{html.escape(title or "")}'

    def video(self, src, alt="", title=None):
        return f'<video src="{html.escape(src)}" controls muted playsinline>{alt}</video><br>{title or ""}'

    def tweet(self, src, alt="", title=None):
        return f'<a href="{html.escape(src)}">{html.escape(src)}</a><br>{html.escape(title or "")}'

    def heading(self, text, level, **attrs):
        tag = f"h{level}"
        return f"<{tag}>{text}</{tag}>\n"
