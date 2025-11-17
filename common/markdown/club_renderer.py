import html
import mistune
from urllib.parse import unquote

from slugify import slugify

from common.markdown.common import split_title_and_css_classes, normalize_url
from common.regexp import IMAGE_RE, VIDEO_RE, YOUTUBE_RE, TWITTER_RE, USERNAME_RE


class ClubRenderer(mistune.HTMLRenderer):
    def __init__(self, uniq_id=None, disable_mentions=False):
        super().__init__()
        self.uniq_id = uniq_id
        self.disable_mentions = disable_mentions

    def text(self, text):
        text = html.escape(text)
        if not self.disable_mentions:
            text = USERNAME_RE.sub(r' <a href="/user/\1/">@\1</a>', text)
        return text

    def paragraph(self, text):
        text = text.replace("\n", "<br>\n")  # Mistune 2.0 broke newlines, let's hack it =/
        return f"<p>{text}</p>\n"

    def heading(self, text, level, **attrs):
        tag = f"h{level}"
        anchor = slugify(text[:24])
        return f"<{tag} id=\"{anchor}\"><a href=\"#{anchor}\">{text}</a></{tag}>\n"

    def link(self, text, url, title=None):
        if text == url:
            # it's a pure link (without link tag) and we can try to parse it
            embed = self.embed(url, text or "", title or "")
            if embed:
                return embed

        link = normalize_url(url)
        text, css_classes = split_title_and_css_classes(text or "")

        if text is None:
            text = link

        # here's some magic of unescape->unquote->escape
        # to fix cyrillic (and other non-latin) wikipedia URLs
        return (f'<a class="{' '.join(css_classes)}" '
                f'href="{self.safe_url(link)}">{html.escape(unquote(html.unescape(text or link)))}</a>')

    def image(self, text, url, title=None):
        # try to detect embed
        embed = self.embed(url, text, title)
        if embed:
            return embed

        # users can try to "hack" our parser by using non-image urls
        # so, if its not an image or video, display it as a link to avoid auto-loading
        return f'<a href="{html.escape(url)}">{html.escape(url)}</a>'

    def embed(self, url, text="", title=None):
        if IMAGE_RE.match(url):
            return self.simple_image(url, text, title)

        if YOUTUBE_RE.match(url):
            return self.youtube(url, text, title)

        if VIDEO_RE.match(url):
            return self.video(url, text, title)

        if TWITTER_RE.match(url):
            return self.tweet(url, text, title)

        return None

    def simple_image(self, url, text="", title=None):
        title, css_classes = split_title_and_css_classes(title or text)
        image_tag = f'<img src="{html.escape(url)}" alt="{html.escape(title)}">'
        caption = f"<figcaption>{html.escape(title)}</figcaption>" if title else ""
        return f'<figure class="{' '.join(css_classes)}">{image_tag}{caption}</figure>'

    def youtube(self, url, text="", title=None):
        youtube_match = YOUTUBE_RE.match(url)
        playlist = ""
        if youtube_match.group(2):
            playlist = f"list={html.escape(youtube_match.group(2))}&listType=playlist&"
        video_tag = (
            f'<span class="ratio-16-9">'
            f'<iframe loading="lazy" src="https://www.youtube.com/embed/{html.escape(youtube_match.group(1) or "")}'
            f'?{playlist}autoplay=0&amp;controls=1&amp;showinfo=1&amp;vq=hd1080"'
            f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen"'
            f'allowfullscreen></iframe>'
            f"</span>"
        )
        caption = f"<figcaption>{html.escape(title)}</figcaption>" if title else ""
        return f"<figure>{video_tag}{caption}</figure>"

    def video(self, url, text="", title=None):
        title, css_classes = split_title_and_css_classes(title or text)
        video_tag = (
            f'<video src="{html.escape(url)}" controls playsinline>{html.escape(text)}</video>'
        )
        caption = f"<figcaption>{html.escape(title)}</figcaption>" if title else ""
        return f'<figure class="{' '.join(css_classes)}">{video_tag}{caption}</figure>'

    def tweet(self, url, text="", title=None):
        tweet_match = TWITTER_RE.match(url)
        twitter_tag = f'<blockquote class="twitter-tweet" tw-align-center>' \
                      f'<a href="{tweet_match.group(1)}"></a></blockquote><br>' \
                      f'<a href="{url}" target="_blank">{url}</a>'
        return twitter_tag
