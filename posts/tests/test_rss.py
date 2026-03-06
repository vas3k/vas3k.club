from datetime import datetime, timedelta

from django.test import TestCase, Client

from posts.models.post import Post
from users.models.user import User


def _create_user(slug, **kwargs):
    defaults = dict(
        email=f"{slug}@test.com",
        full_name=slug,
        membership_started_at=datetime.utcnow() - timedelta(days=5),
        membership_expires_at=datetime.utcnow() + timedelta(days=365),
        moderation_status=User.MODERATION_STATUS_APPROVED,
        is_email_verified=True,
    )
    defaults.update(kwargs)
    return User.objects.create(slug=slug, **defaults)


def _create_post(slug, author, **kwargs):
    defaults = dict(
        title=f"Post {slug}",
        text=f"Text of {slug}",
        type=Post.TYPE_POST,
        visibility=Post.VISIBILITY_EVERYWHERE,
        published_at=datetime.utcnow() - timedelta(hours=1),
        last_activity_at=datetime.utcnow() - timedelta(hours=1),
        moderation_status=Post.MODERATION_APPROVED,
        is_public=True,
    )
    defaults.update(kwargs)
    return Post.objects.create(slug=slug, author=author, **defaults)


class TestNewPostsRss(TestCase):

    def setUp(self):
        self.user = _create_user("rss_user")
        self.client = Client()

    def test_approved_public_post_in_rss(self):
        _create_post("rss_visible", self.user)

        response = self.client.get("/posts.rss")

        self.assertEqual(response.status_code, 200)
        self.assertIn("rss_visible", response.content.decode())

    def test_only_approved_posts_in_rss(self):
        _create_post("rss_approved", self.user)
        _create_post("rss_pending", self.user, moderation_status=Post.MODERATION_PENDING)
        _create_post("rss_none", self.user, moderation_status=Post.MODERATION_NONE)

        content = self.client.get("/posts.rss").content.decode()

        self.assertIn("rss_approved", content)
        self.assertNotIn("rss_pending", content)
        self.assertNotIn("rss_none", content)

    def test_private_post_shown_in_rss(self):
        _create_post("rss_private", self.user, is_public=False)

        content = self.client.get("/posts.rss").content.decode()

        self.assertIn("rss_private", content)

    def test_description_is_truncated(self):
        long_text = "A" * 500
        _create_post("rss_long", self.user, text=long_text)

        content = self.client.get("/posts.rss").content.decode()

        self.assertIn("rss_long", content)
        self.assertNotIn("A" * 500, content)

    def test_intro_posts_excluded(self):
        _create_post("rss_intro", self.user, type=Post.TYPE_INTRO)

        content = self.client.get("/posts.rss").content.decode()

        self.assertNotIn("rss_intro", content)


class TestUserPostsRss(TestCase):

    def setUp(self):
        self.user = _create_user("rss_author")
        self.other = _create_user("rss_other")
        self.client = Client()

    def test_shows_only_user_posts(self):
        _create_post("urss_mine", self.user)
        _create_post("urss_other", self.other)

        content = self.client.get(f"/user/{self.user.slug}/posts.rss").content.decode()

        self.assertIn("urss_mine", content)
        self.assertNotIn("urss_other", content)

    def test_only_approved_posts(self):
        _create_post("urss_approved", self.user)
        _create_post("urss_pending", self.user, moderation_status=Post.MODERATION_PENDING)
        _create_post("urss_none", self.user, moderation_status=Post.MODERATION_NONE)

        content = self.client.get(f"/user/{self.user.slug}/posts.rss").content.decode()

        self.assertIn("urss_approved", content)
        self.assertNotIn("urss_pending", content)
        self.assertNotIn("urss_none", content)

    def test_private_post_shown_in_user_rss(self):
        _create_post("urss_private", self.user, is_public=False)

        content = self.client.get(f"/user/{self.user.slug}/posts.rss").content.decode()

        self.assertIn("urss_private", content)

    def test_nonexistent_user_returns_404(self):
        response = self.client.get("/user/no_such_user/posts.rss")
        self.assertEqual(response.status_code, 404)
