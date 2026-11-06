from datetime import datetime, timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from debug.utils_for_tests import create_approved_user
from misc.models import ProTip
from notifications.digests import generate_daily_digest, generate_weekly_digest
from posts.models.post import Post
from users.models.user import User


@override_settings(DEBUG=False, CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class HistoricalDigestSelectionTest(TestCase):
    def test_historical_pick_excludes_toxic_and_hidden_posts(self):
        user = create_approved_user("historical-digest")
        ProTip.objects.create(title="Tip", text="Be nice", is_visible=True)
        Post.objects.create(
            author=user, slug="recent", type=Post.TYPE_POST,
            visibility=Post.VISIBILITY_EVERYWHERE, moderation_status=Post.MODERATION_APPROVED,
        )
        eligible = Post.objects.create(
            author=user, slug="eligible", type=Post.TYPE_POST, upvotes=50,
            visibility=Post.VISIBILITY_EVERYWHERE, moderation_status=Post.MODERATION_APPROVED,
            published_at=datetime.utcnow() - timedelta(days=366),
        )

        for generator in [generate_daily_digest, generate_weekly_digest]:
            for index, hidden_fields in enumerate([
                {"label_code": "toxic"},
                {"is_room_only": True},
                {"visibility": Post.VISIBILITY_DRAFT},
                {"visibility": Post.VISIBILITY_LINK_ONLY},
            ]):
                with self.subTest(generator=generator.__name__, hidden_fields=hidden_fields):
                    cache.clear()
                    hidden = Post.objects.create(
                        author=user, slug=f"hidden-{generator.__name__}-{index}", type=Post.TYPE_POST, upvotes=100,
                        moderation_status=Post.MODERATION_APPROVED,
                        published_at=eligible.published_at,
                        **{"visibility": Post.VISIBILITY_EVERYWHERE, **hidden_fields},
                    )

                    if generator == generate_daily_digest:
                        cache.set(f"daily_digest:top_old_post:{datetime.utcnow().date()}:False", [hidden])

                    with patch("notifications.digests.render_to_string", return_value="") as render:
                        if generator == generate_daily_digest:
                            generator(user)
                        else:
                            generator()

                    hidden.delete()
                    self.assertEqual(render.call_args.args[1]["top_old_post"], eligible)


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
