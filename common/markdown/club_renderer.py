import mistune
from mistune import escape_html

from common.regexp import IMAGE_RE, VIDEO_RE, YOUTUBE_RE, TWITTER_RE, USERNAME_RE


class ClubRenderer(mistune.HTMLRenderer):
    def text(self, text):
        text = escape_html(text)
        text = USERNAME_RE.sub(r'<a href="/user/\1/">@\1</a>', text)
        return text

    def link(self, link, text=None, title=None):
        if IMAGE_RE.match(link):
            return self.image(link, text or "", title or "")

        if YOUTUBE_RE.match(link):
            return self.youtube(link, text, title)

        if VIDEO_RE.match(link):
            return self.video(link, text, title)

        if TWITTER_RE.match(link):
            return self.tweet(link, text, title)

        return super().link(link, text, title)

    def image(self, src, alt="", title=None):
        if IMAGE_RE.match(src):
            return self.just_img(src, alt, title)

        if YOUTUBE_RE.match(src):
            return self.youtube(src, alt, title)

        if VIDEO_RE.match(src):
            return self.video(src, alt, title)

        if TWITTER_RE.match(src):
            return self.tweet(src, alt, title)

        # if its not an image or video, display as a link
        return f'<a href="{src}">{src}</a>'

    def just_img(self, src, alt="", title=None):
        image_tag = f'<img src="{src}" alt="{alt}">'
        caption = f"<figcaption>{escape_html(title)}</figcaption>" if title else ""
        return f"<figure>{image_tag}{caption}</figure>"

    def youtube(self, src, alt="", title=None):
        youtube_match = YOUTUBE_RE.match(src)
        video_tag = (
            f'<span class="ratio-16-9">'
            f'<iframe src="https://www.youtube.com/embed/{escape_html(youtube_match.group(1))}'
            f'?autoplay=0&amp;controls=1&amp;showinfo=1&amp;vq=hd1080" frameborder="0"></iframe>'
            f"</span>"
        )
        caption = f"<figcaption>{escape_html(title)}</figcaption>" if title else ""
        return f"<figure>{video_tag}{caption}</figure>"

    def video(self, src, alt="", title=None):
        video_tag = (
            f'<video src="{src}" controls autoplay loop muted playsinline>{alt}</video>'
        )
        caption = f"<figcaption>{escape_html(title)}</figcaption>" if title else ""
        return f"<figure>{video_tag}{caption}</figure>"

    def tweet(self, src, alt="", title=None):
        tweet_match = TWITTER_RE.match(src)
        twitter_tag = f'<blockquote class="twitter-tweet" tw-align-center>' \
                      f'<a href="{tweet_match.group(1)}"></a></blockquote>'
        return twitter_tag
