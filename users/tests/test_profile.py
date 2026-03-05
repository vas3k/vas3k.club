from datetime import datetime, timedelta

from django.test import TestCase, Client

from authn.models.session import Session
from comments.models import Comment
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


def _create_comment(post, author, **kwargs):
    defaults = dict(
        text="Test comment",
        created_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return Comment.objects.create(post=post, author=author, **defaults)


def _login(client, user):
    session = Session.create_for_user(user)
    client.cookies["token"] = session.token


class TestProfilePostsTotal(TestCase):
    """Test that posts_total in profile context is accurate."""

    def setUp(self):
        self.user = _create_user("tprof_user")
        self.viewer = _create_user("tprof_viewer")
        self.client = Client()
        _login(self.client, self.viewer)

    def test_posts_total_counts_visible_posts(self):
        for i in range(5):
            _create_post(f"tprof_post_{i}", self.user)

        response = self.client.get(f"/user/{self.user.slug}/")
        self.assertEqual(response.context["posts_total"], 5)

    def test_posts_total_excludes_intros(self):
        _create_post("tprof_intro", self.user, type=Post.TYPE_INTRO)
        _create_post("tprof_regular", self.user)

        response = self.client.get(f"/user/{self.user.slug}/")
        self.assertEqual(response.context["posts_total"], 1)

    def test_posts_total_excludes_drafts(self):
        _create_post("tprof_draft", self.user, visibility=Post.VISIBILITY_DRAFT)
        _create_post("tprof_visible", self.user)

        response = self.client.get(f"/user/{self.user.slug}/")
        self.assertEqual(response.context["posts_total"], 1)

    def test_posts_total_excludes_digests(self):
        _create_post("tprof_digest", self.user, type=Post.TYPE_WEEKLY_DIGEST)
        _create_post("tprof_normal", self.user)

        response = self.client.get(f"/user/{self.user.slug}/")
        self.assertEqual(response.context["posts_total"], 1)

    def test_posts_total_zero_when_no_posts(self):
        response = self.client.get(f"/user/{self.user.slug}/")
        self.assertEqual(response.context["posts_total"], 0)

    def test_posts_slice_limited_to_15(self):
        for i in range(20):
            _create_post(f"tprof_many_{i}", self.user)

        response = self.client.get(f"/user/{self.user.slug}/")
        self.assertEqual(len(response.context["posts"]), 15)
        self.assertEqual(response.context["posts_total"], 20)

    def test_posts_total_includes_coauthored(self):
        other = _create_user("tprof_other")
        _create_post("tprof_coauth", other, coauthors=[self.user.slug])
        _create_post("tprof_own", self.user)

        response = self.client.get(f"/user/{self.user.slug}/")
        self.assertEqual(response.context["posts_total"], 2)

    def test_posts_total_excludes_link_only_for_other_user(self):
        _create_post("tprof_link", self.user, visibility=Post.VISIBILITY_LINK_ONLY)
        _create_post("tprof_pub", self.user)

        response = self.client.get(f"/user/{self.user.slug}/")
        self.assertEqual(response.context["posts_total"], 1)

    def test_posts_total_includes_own_link_only(self):
        _create_post("tprof_own_link", self.viewer, visibility=Post.VISIBILITY_LINK_ONLY)
        _create_post("tprof_own_pub", self.viewer)

        response = self.client.get(f"/user/{self.viewer.slug}/")
        self.assertEqual(response.context["posts_total"], 2)


class TestProfileCommentsTotal(TestCase):
    """Test that comments_total in profile context is accurate."""

    def setUp(self):
        self.user = _create_user("tcprof_user")
        self.viewer = _create_user("tcprof_viewer")
        self.client = Client()
        _login(self.client, self.viewer)

    def test_comments_total_counts_visible(self):
        post = _create_post("tcprof_post", self.user)
        for i in range(4):
            _create_comment(post, self.user)

        response = self.client.get(f"/user/{self.user.slug}/")
        self.assertEqual(response.context["comments_total"], 4)

    def test_comments_total_excludes_draft_post_comments(self):
        visible_post = _create_post("tcprof_vis", self.user)
        draft_post = _create_post("tcprof_draft", self.user,
                                  visibility=Post.VISIBILITY_DRAFT)
        _create_comment(visible_post, self.user)
        _create_comment(draft_post, self.user)

        response = self.client.get(f"/user/{self.user.slug}/")
        self.assertEqual(response.context["comments_total"], 1)

    def test_comments_total_zero_when_no_comments(self):
        response = self.client.get(f"/user/{self.user.slug}/")
        self.assertEqual(response.context["comments_total"], 0)

    def test_comments_slice_limited_to_3(self):
        post = _create_post("tcprof_post", self.user)
        for i in range(6):
            _create_comment(post, self.user)

        response = self.client.get(f"/user/{self.user.slug}/")
        self.assertEqual(len(response.context["comments"]), 3)
        self.assertEqual(response.context["comments_total"], 6)
