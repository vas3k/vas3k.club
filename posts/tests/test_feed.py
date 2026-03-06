from datetime import datetime, timedelta

from django.db import connection, reset_queries
from django.test import TestCase, Client

from authn.models.session import Session
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
        moderation_status=Post.MODERATION_NONE,
    )
    defaults.update(kwargs)
    return Post.objects.create(slug=slug, author=author, **defaults)


def _login(client, user):
    session = Session.create_for_user(user)
    client.cookies["token"] = session.token


class TestFeedPinnedPosts(TestCase):
    """Test that pinned posts appear separately and are excluded from the main feed."""

    def setUp(self):
        self.user = _create_user("tfeed_user")
        self.client = Client()
        _login(self.client, self.user)

    def test_pinned_post_appears_in_pinned_list(self):
        pinned = _create_post("tfeed_pinned", self.user,
                              is_pinned_until=datetime.utcnow() + timedelta(days=1))

        response = self.client.get("/")
        pinned_posts = list(response.context["pinned_posts"])

        self.assertEqual(len(pinned_posts), 1)
        self.assertEqual(pinned_posts[0].id, pinned.id)

    def test_pinned_post_excluded_from_main_feed(self):
        pinned = _create_post("tfeed_pinned", self.user,
                              is_pinned_until=datetime.utcnow() + timedelta(days=1))
        regular = _create_post("tfeed_regular", self.user)

        response = self.client.get("/")
        feed_ids = [p.id for p in response.context["posts"]]

        self.assertNotIn(pinned.id, feed_ids)
        self.assertIn(regular.id, feed_ids)

    def test_expired_pinned_post_in_main_feed(self):
        expired = _create_post("tfeed_expired", self.user,
                               is_pinned_until=datetime.utcnow() - timedelta(hours=1))

        response = self.client.get("/")
        pinned_posts = list(response.context["pinned_posts"])
        feed_ids = [p.id for p in response.context["posts"]]

        self.assertEqual(len(pinned_posts), 0)
        self.assertIn(expired.id, feed_ids)

    def test_null_pinned_until_in_main_feed(self):
        regular = _create_post("tfeed_null_pin", self.user, is_pinned_until=None)

        response = self.client.get("/")
        pinned_posts = list(response.context["pinned_posts"])
        feed_ids = [p.id for p in response.context["posts"]]

        self.assertEqual(len(pinned_posts), 0)
        self.assertIn(regular.id, feed_ids)

    def test_multiple_regular_posts_not_lost(self):
        posts = []
        for i in range(5):
            posts.append(_create_post(f"tfeed_reg_{i}", self.user))

        response = self.client.get("/")
        feed_ids = [p.id for p in response.context["posts"]]

        for p in posts:
            self.assertIn(p.id, feed_ids)

    def test_pinned_and_regular_together(self):
        pinned = _create_post("tfeed_pinned", self.user,
                              is_pinned_until=datetime.utcnow() + timedelta(days=1))
        regulars = [_create_post(f"tfeed_reg_{i}", self.user) for i in range(3)]

        response = self.client.get("/")
        pinned_posts = list(response.context["pinned_posts"])
        feed_ids = [p.id for p in response.context["posts"]]

        self.assertEqual(len(pinned_posts), 1)
        self.assertEqual(pinned_posts[0].id, pinned.id)
        self.assertNotIn(pinned.id, feed_ids)
        for r in regulars:
            self.assertIn(r.id, feed_ids)

    def test_draft_posts_excluded(self):
        draft = _create_post("tfeed_draft", self.user,
                             visibility=Post.VISIBILITY_DRAFT)

        response = self.client.get("/")
        feed_ids = [p.id for p in response.context["posts"]]

        self.assertNotIn(draft.id, feed_ids)

    def test_non_activity_ordering_skips_pinning(self):
        pinned = _create_post("tfeed_pinned_new", self.user,
                              is_pinned_until=datetime.utcnow() + timedelta(days=1))

        response = self.client.get("/all/new/")
        pinned_posts = response.context["pinned_posts"]
        feed_ids = [p.id for p in response.context["posts"]]

        self.assertEqual(pinned_posts, [])
        self.assertIn(pinned.id, feed_ids)
