from mistune import escape_html

from common.markdown.club_renderer import ClubRenderer
from common.regexp import YOUTUBE_RE


class EmailRenderer(ClubRenderer):
    def simple_image(self, src, alt="", title=None):
        return f"""<img src="{src}" alt="{alt}" width="600" border="0"><br>{title or ""}"""

    def youtube(self, src, alt="", title=None):
        youtube_match = YOUTUBE_RE.match(src)
        youtube_id = escape_html(youtube_match.group(1) or "")
        return f'<a href="{escape_html(src)}"><span class="ratio-16-9 video-preview" ' \
               f'style="background-image: url(\'https://img.youtube.com/vi/{escape_html(youtube_id)}/0.jpg\');">' \
               f'</span></a><br>{escape_html(title or "")}'

    def video(self, src, alt="", title=None):
        return f'<video src="{escape_html(src)}" controls muted playsinline>{alt}</video><br>{title or ""}'

    def tweet(self, src, alt="", title=None):
        return f'<a href="{escape_html(src)}">{escape_html(src)}</a><br>{escape_html(title or "")}'

    def heading(self, text, level):
        tag = f"h{level}"
        return f"<{tag}>{text}</{tag}>\n"
