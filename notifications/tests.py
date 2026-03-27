from datetime import datetime, timedelta

from django.test import TestCase, override_settings

from misc.models import ProTip
from notifications.digests import generate_weekly_digest
from posts.models.post import Post
from users.models.user import User


@override_settings(APP_HOST="https://test.club")
class WeeklyDigestRenderingTest(TestCase):

    def setUp(self):
        self.user = User.objects.create(
            slug="digest_user",
            email="digest@test.com",
            full_name="Test User",
            membership_started_at=datetime.utcnow() - timedelta(days=5),
            membership_expires_at=datetime.utcnow() + timedelta(days=365),
            moderation_status=User.MODERATION_STATUS_APPROVED,
        )
        ProTip.objects.create(title="Tip", text="Be nice", is_visible=True)

    def _create_post(self, **kwargs):
        defaults = dict(
            author=self.user,
            visibility=Post.VISIBILITY_EVERYWHERE,
            moderation_status=Post.MODERATION_APPROVED,
            published_at=datetime.utcnow() - timedelta(hours=1),
        )
        defaults.update(kwargs)
        return Post.objects.create(**defaults)

    def test_digest_renders_intro_as_plain_text(self):
        self._create_post(
            slug="intro_md",
            type=Post.TYPE_INTRO,
            title="My Intro",
            text="Hello, I am **bold** dev with [portfolio](https://example.com/very/long/path) " * 20,
            upvotes=10,
        )
        self._create_post(
            slug="filler_post",
            type=Post.TYPE_POST,
            title="Filler",
            text="Some post",
            upvotes=1,
        )

        html, _ = generate_weekly_digest()

        self.assertIn("Test User", html)
        self.assertIn("bold", html)
        self.assertNotIn("[portfolio]", html)
        self.assertNotIn("**bold**", html)

    def test_digest_renders_post_preview_as_plain_text(self):
        self._create_post(
            slug="post_md",
            type=Post.TYPE_POST,
            title="Great Post",
            text="Read [this article](https://example.com) about **testing** " * 30,
            upvotes=5,
        )

        html, _ = generate_weekly_digest()

        self.assertIn("Great Post", html)
        self.assertIn("this article", html)
        self.assertNotIn("[this article]", html)

    def test_digest_truncates_long_post_preview(self):
        long_text = "A" * 1000
        self._create_post(
            slug="long_post",
            type=Post.TYPE_POST,
            title="Long Post",
            text=long_text,
            upvotes=5,
        )

        html, _ = generate_weekly_digest()

        self.assertIn("Long Post", html)
        self.assertIn("…", html)
        self.assertNotIn("A" * 500, html)
