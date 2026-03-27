from datetime import datetime, timedelta

from django.test import TestCase, Client

from authn.models.session import Session
from comments.models import Comment
from posts.models.post import Post
from search.models import SearchIndex
from users.models.user import User


def _create_user(slug, **kwargs):
    defaults = dict(
        email=f"{slug}@test.com",
        full_name=f"User {slug}",
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
    )
    defaults.update(kwargs)
    return Post.objects.create(slug=slug, author=author, **defaults)


def _login(client, user):
    session = Session.create_for_user(user)
    client.cookies["token"] = session.token


class TestSearchRendersAuthors(TestCase):

    def setUp(self):
        self.viewer = _create_user("tsearch_viewer")
        self.client = Client()
        _login(self.client, self.viewer)

        for i in range(3):
            author = _create_user(f"tsearch_author_{i}")
            post = _create_post(
                f"tsearch_python_{i}", author, title=f"Python guide part {i}",
            )
            SearchIndex.update_post_index(post)

        base_post = _create_post("tsearch_base", self.viewer, title="Python base post")
        SearchIndex.update_post_index(base_post)
        commenter = _create_user("tsearch_commenter")
        comment = Comment.objects.create(
            post=base_post, author=commenter,
            text="Python comment", created_at=datetime.utcnow(),
        )
        SearchIndex.update_comment_index(comment)

    def test_post_authors_rendered(self):
        response = self.client.get("/search/?q=python&type=post")
        content = response.content.decode()
        self.assertIn("tsearch_author_0", content)
        self.assertIn("tsearch_author_1", content)

    def test_comment_author_rendered(self):
        response = self.client.get("/search/?q=python&type=comment")
        content = response.content.decode()
        self.assertIn("tsearch_commenter", content)

    def test_comment_post_title_rendered(self):
        response = self.client.get("/search/?q=python&type=comment")
        content = response.content.decode()
        self.assertIn("Python base post", content)
