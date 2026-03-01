from datetime import datetime, timedelta

from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.utils.safestring import SafeString

from comments.models import Comment
from common.markdown.markdown import markdown_text
from comments.templatetags.comments import render_comment
from posts.models.post import Post
from users.models.user import User


class TestRenderComment(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email="comment_tag_test@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            slug="comment_tag_user",
        )
        self.post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="comment_tag_post",
            title="Test Post",
            text="Hello",
            author=self.user,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )
        self.comment = Comment.objects.create(
            author=self.user,
            post=self.post,
            text="Test **comment** body",
        )

    def test_renders_markdown_to_html(self):
        Comment.objects.filter(id=self.comment.id).update(html="")
        self.comment.refresh_from_db()

        context = {"request": None}
        result = render_comment(context, self.comment)

        self.assertIsInstance(result, SafeString)
        self.assertIn("comment", result)

    def test_caches_html_on_comment(self):
        Comment.objects.filter(id=self.comment.id).update(html="")
        self.comment.refresh_from_db()

        context = {"request": None}
        render_comment(context, self.comment)

        self.comment.refresh_from_db()
        self.assertTrue(len(self.comment.html) > 0)

    def test_save_uses_update_fields(self):
        """save() should UPDATE only html and updated_at, not all columns."""
        Comment.objects.filter(id=self.comment.id).update(html="")
        self.comment.refresh_from_db()

        new_html = markdown_text(self.comment.text, uniq_id=self.comment.id)
        self.assertNotEqual(new_html, self.comment.html, "html must differ to trigger save")

        context = {"request": None}
        with CaptureQueriesContext(connection) as queries:
            render_comment(context, self.comment)

        update_queries = [q["sql"] for q in queries if q["sql"].startswith("UPDATE")]
        self.assertEqual(len(update_queries), 1)

        sql = update_queries[0]
        self.assertIn("html", sql)
        self.assertNotIn("title", sql)
        self.assertNotIn('"text"', sql)

    def test_deleted_comment_shows_message(self):
        self.comment.is_deleted = True
        self.comment.deleted_by = self.user.id

        context = {"request": None}
        result = render_comment(context, self.comment)

        self.assertIn("удален", result)
