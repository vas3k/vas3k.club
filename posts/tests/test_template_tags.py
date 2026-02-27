from datetime import datetime, timedelta

from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.utils.safestring import SafeString

from common.markdown.markdown import markdown_text
from posts.models.post import Post
from posts.templatetags.posts import render_post
from users.models.user import User


class TestRenderPost(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email="post_tag_test@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            slug="post_tag_user",
        )
        self.post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="post_tag_test",
            title="Test Post",
            text="Hello **world**",
            author=self.user,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )

    def test_renders_markdown_to_html(self):
        Post.objects.filter(id=self.post.id).update(html="")
        self.post.refresh_from_db()

        context = {"request": None}
        result = render_post(context, self.post)

        self.assertIsInstance(result, SafeString)
        self.assertIn("world", result)

    def test_caches_html_on_post(self):
        Post.objects.filter(id=self.post.id).update(html="")
        self.post.refresh_from_db()

        context = {"request": None}
        render_post(context, self.post)

        self.post.refresh_from_db()
        self.assertTrue(len(self.post.html) > 0)

    def test_save_uses_update_fields(self):
        """save() should UPDATE only html and updated_at, not all columns."""
        Post.objects.filter(id=self.post.id).update(html="")
        self.post.refresh_from_db()

        new_html = markdown_text(self.post.text, uniq_id=self.post.id)
        self.assertNotEqual(new_html, self.post.html, "html must differ to trigger save")

        context = {"request": None}
        with CaptureQueriesContext(connection) as queries:
            render_post(context, self.post)

        update_queries = [q["sql"] for q in queries if q["sql"].startswith("UPDATE")]
        self.assertEqual(len(update_queries), 1)

        sql = update_queries[0]
        self.assertIn("html", sql)
        self.assertNotIn("title", sql)
        self.assertNotIn('"text"', sql)
