import html
import mistune
from urllib.parse import unquote
from mistune import escape_html
from slugify import slugify

from common.regexp import IMAGE_RE, VIDEO_RE, YOUTUBE_RE, TWITTER_RE, USERNAME_RE

IMAGE_CSS_CLASSES = {
    "-": "text-body-image-full"
}


class ClubRenderer(mistune.HTMLRenderer):
    def text(self, text):
        text = escape_html(text)
        text = USERNAME_RE.sub(r' <a href="/user/\1/">@\1</a>', text)
        return text

    def paragraph(self, text):
        text = text.replace("\n", "<br>\n")  # Mistune 2.0 broke newlines, let's hack it =/
        return f"<p>{text}</p>\n"

    def heading(self, text, level):
        tag = f"h{level}"
        anchor = slugify(text[:24])
        return f"<{tag} id=\"{anchor}\"><a href=\"#{anchor}\">{text}</a></{tag}>\n"

    def link(self, link, text=None, title=None):
        if not text and not title:
            # it's a pure link (without link tag) and we can try to parse it
            embed = self.embed(link, text or "", title or "")
            if embed:
                return embed

        if text is None:
            text = link

        # here's some magic of unescape->unquote->escape
        # to fix cyrillic (and other non-latin) wikipedia URLs
        return f'<a href="{self._safe_url(link)}">{html.escape(unquote(html.unescape(text or link)))}</a>'

    def image(self, src, alt="", title=None):
        embed = self.embed(src, alt, title)
        if embed:
            return embed

        # users can try to "hack" our parser by using non-image urls
        # so, if its not an image or video, display it as a link to avoid auto-loading
        return f'<a href="{escape_html(src)}">{escape_html(src)}</a>'

    def embed(self, src, alt="", title=None):
        if IMAGE_RE.match(src):
            return self.simple_image(src, alt, title)

        if YOUTUBE_RE.match(src):
            return self.youtube(src, alt, title)

        if VIDEO_RE.match(src):
            return self.video(src, alt, title)

        if TWITTER_RE.match(src):
            return self.tweet(src, alt, title)

        return None

    def simple_image(self, src, alt="", title=None):
        css_classes = ""
        title = title or alt
        if title in IMAGE_CSS_CLASSES:
            css_classes = IMAGE_CSS_CLASSES[title]

        image_tag = f'<img src="{escape_html(src)}" alt="{escape_html(title)}">'
        caption = f"<figcaption>{escape_html(title)}</figcaption>" if title else ""
        return f'<figure class="{css_classes}">{image_tag}{caption}</figure>'

    def youtube(self, src, alt="", title=None):
        youtube_match = YOUTUBE_RE.match(src)
        playlist = ""
        if youtube_match.group(2):
            playlist = f"list={escape_html(youtube_match.group(2))}&listType=playlist&"
        video_tag = (
            f'<span class="ratio-16-9">'
            f'<iframe loading="lazy" src="https://www.youtube.com/embed/{escape_html(youtube_match.group(1) or "")}'
            f'?{playlist}autoplay=0&amp;controls=1&amp;showinfo=1&amp;vq=hd1080"'
            f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen"'
            f'allowfullscreen></iframe>'
            f"</span>"
        )
        caption = f"<figcaption>{escape_html(title)}</figcaption>" if title else ""
        return f"<figure>{video_tag}{caption}</figure>"

    def video(self, src, alt="", title=None):
        video_tag = (
            f'<video src="{escape_html(src)}" controls muted playsinline>{escape_html(alt)}</video>'
        )
        caption = f"<figcaption>{escape_html(title)}</figcaption>" if title else ""
        return f"<figure>{video_tag}{caption}</figure>"

    def tweet(self, src, alt="", title=None):
        tweet_match = TWITTER_RE.match(src)
        twitter_tag = f'<blockquote class="twitter-tweet" tw-align-center>' \
                      f'<a href="{tweet_match.group(1)}"></a></blockquote><br>' \
                      f'<a href="{src}" target="_blank">{src}</a>'
        return twitter_tag
