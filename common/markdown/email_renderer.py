from mistune import escape_html

from common.markdown.club_renderer import ClubRenderer, YOUTUBE_RE


class EmailRenderer(ClubRenderer):
    def just_img(self, src, alt="", title=None):
        return f"""<img src="{src}" alt="{alt}" width="600" border="0"><br>{title or ""}"""

    def youtube(self, src, alt="", title=None):
        youtube_match = YOUTUBE_RE.match(src)
        youtube_id = escape_html(youtube_match.group(1))
        return f'<a href="{src}"><span class="ratio-16-9 video-preview" ' \
               f'style="background-image: url(\'https://img.youtube.com/vi/{youtube_id}/0.jpg\');">' \
               f'</span></a><br>{title or ""}'

    def video(self, src, alt="", title=None):
        return f'<video src="{src}" controls autoplay loop muted playsinline>{alt}</video><br>{title or ""}'

    def tweet(self, src, alt="", title=None):
        return f'<a href="{src}">{src}</a><br>{title or ""}'
