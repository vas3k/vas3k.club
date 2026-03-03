from datetime import datetime, timedelta

from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.utils.safestring import SafeString

from comments.models import Comment
from common.markdown.markdown import markdown_text
from comments.templatetags.comments import comment_tree, render_comment, TreeComment
from posts.models.post import Post
from posts.renderers import _warm_comment_html_cache
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


class TestCommentTree(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email="tree_test@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            slug="tree_test_user",
        )
        self.post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="tree_test_post",
            title="Test Post",
            text="Hello",
            author=self.user,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )

    def _create_comment(self, **kwargs):
        return Comment.objects.create(
            author=self.user,
            post=self.post,
            text="text",
            **kwargs,
        )

    def test_empty_list(self):
        self.assertEqual(comment_tree([]), [])

    def test_top_level_only(self):
        c1 = self._create_comment()
        c2 = self._create_comment()

        tree = comment_tree(Comment.objects.filter(post=self.post).order_by("created_at"))

        self.assertEqual(len(tree), 2)
        self.assertEqual(tree[0].comment.id, c1.id)
        self.assertEqual(tree[1].comment.id, c2.id)
        self.assertEqual(tree[0].replies, [])

    def test_three_level_nesting(self):
        top = self._create_comment()
        reply = self._create_comment(reply_to=top)
        deep = self._create_comment(reply_to=reply)

        tree = comment_tree(Comment.objects.filter(post=self.post).order_by("created_at"))

        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0].comment.id, top.id)
        self.assertEqual(len(tree[0].replies), 1)
        self.assertEqual(tree[0].replies[0].comment.id, reply.id)
        self.assertEqual(len(tree[0].replies[0].replies), 1)
        self.assertEqual(tree[0].replies[0].replies[0].id, deep.id)

    def test_replies_sorted_by_created_at(self):
        top = self._create_comment()
        r1 = self._create_comment(reply_to=top)
        r2 = self._create_comment(reply_to=top)

        tree = comment_tree(Comment.objects.filter(post=self.post))

        reply_ids = [r.comment.id for r in tree[0].replies]
        self.assertEqual(reply_ids, [r1.id, r2.id])

    def test_pinned_comment_first(self):
        c1 = self._create_comment()
        c2 = self._create_comment(is_pinned=True)

        tree = comment_tree(Comment.objects.filter(post=self.post))

        self.assertEqual(tree[0].comment.id, c2.id)
        self.assertEqual(tree[1].comment.id, c1.id)

    def test_returns_tree_comment_namedtuples(self):
        top = self._create_comment()
        self._create_comment(reply_to=top)

        tree = comment_tree(Comment.objects.filter(post=self.post))

        self.assertIsInstance(tree[0], TreeComment)
        self.assertIsInstance(tree[0].replies[0], TreeComment)


class TestWarmCommentHtmlCache(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email="warm_cache_test@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            slug="warm_cache_user",
        )
        self.post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="warm_cache_post",
            title="Test Post",
            text="Hello",
            author=self.user,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )

    def _create_comment(self, **kwargs):
        defaults = dict(author=self.user, post=self.post, text="**bold**")
        defaults.update(kwargs)
        return Comment.objects.create(**defaults)

    @override_settings(DEBUG=False)
    def test_generates_html_for_comments_without_cache(self):
        c = self._create_comment()
        Comment.objects.filter(id=c.id).update(html=None)
        c.refresh_from_db()

        comments = list(Comment.objects.filter(post=self.post))
        _warm_comment_html_cache(comments)

        c.refresh_from_db()
        self.assertIsNotNone(c.html)
        self.assertIn("bold", c.html)

    @override_settings(DEBUG=False)
    def test_skips_comments_with_existing_html(self):
        c = self._create_comment()
        existing_html = "<p>cached</p>"
        Comment.objects.filter(id=c.id).update(html=existing_html)
        c.refresh_from_db()

        comments = list(Comment.objects.filter(post=self.post))
        _warm_comment_html_cache(comments)

        c.refresh_from_db()
        self.assertEqual(c.html, existing_html)

    @override_settings(DEBUG=False)
    def test_skips_deleted_comments(self):
        c = self._create_comment()
        c.delete(deleted_by=self.user)
        Comment.objects.filter(id=c.id).update(html=None)
        c.refresh_from_db()

        comments = list(Comment.objects.filter(post=self.post))
        _warm_comment_html_cache(comments)

        c.refresh_from_db()
        self.assertIsNone(c.html)

    @override_settings(DEBUG=True)
    def test_noop_in_debug_mode(self):
        c = self._create_comment()
        Comment.objects.filter(id=c.id).update(html=None)
        c.refresh_from_db()

        comments = list(Comment.objects.filter(post=self.post))
        _warm_comment_html_cache(comments)

        c.refresh_from_db()
        self.assertIsNone(c.html)

    @override_settings(DEBUG=False)
    def test_single_bulk_update_instead_of_n_saves(self):
        for i in range(5):
            self._create_comment(text=f"comment {i}")
        Comment.objects.filter(post=self.post).update(html=None)

        comments = list(Comment.objects.filter(post=self.post))
        with CaptureQueriesContext(connection) as queries:
            _warm_comment_html_cache(comments)

        update_queries = [q for q in queries if q["sql"].startswith("UPDATE")]
        self.assertEqual(len(update_queries), 1)
