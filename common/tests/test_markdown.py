from django.test import SimpleTestCase

from common.markdown.markdown import markdown_text, markdown_email


class TestMarkdownImageCaption(SimpleTestCase):

    def test_quotes_in_caption_are_escaped_once(self):
        html = markdown_text('![Say "hi" & <b>bye</b>](https://i.vas3k.club/photo.jpg)')

        self.assertIn("<figcaption>Say &quot;hi&quot; &amp; &lt;b&gt;bye&lt;/b&gt;</figcaption>", html)
        self.assertNotIn("&amp;quot;", html)
        self.assertNotIn("<b>", html)

    def test_bold_in_caption_is_rendered_but_plain_in_alt(self):
        html = markdown_text("![Some **bold** words](https://i.vas3k.club/photo.jpg)")

        self.assertIn("<figcaption>Some <strong>bold</strong> words</figcaption>", html)
        self.assertIn('alt="Some bold words"', html)

    def test_mention_in_caption_is_link_but_plain_in_alt(self):
        html = markdown_text("![Taken by @vas3k](https://i.vas3k.club/photo.jpg)")

        self.assertIn('<a href="/user/vas3k/">@vas3k</a></figcaption>', html)
        self.assertIn('alt="Taken by @vas3k"', html)

    def test_quotes_in_email_image_alt_are_escaped_once(self):
        html = markdown_email('![Say "hi"](https://i.vas3k.club/photo.jpg)')

        self.assertIn('alt="Say &quot;hi&quot;"', html)
        self.assertNotIn("&amp;quot;", html)

    def test_bold_in_email_image_alt_is_plain_text(self):
        html = markdown_email("![Some **bold** words](https://i.vas3k.club/photo.jpg)")

        self.assertIn('alt="Some bold words"', html)
