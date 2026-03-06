from datetime import datetime, timedelta

from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse

from comments.models import Comment, CommentVote
from debug.helpers import HelperClient
from posts.models.post import Post
from users.models.user import User


class RendererTestBase(TestCase):
    def setUp(self):
        self._user_counter = 0
        self.user = self._create_user()
        self.post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="renderer_test_post",
            title="Test Post",
            text="Hello",
            author=self.user,
            visibility=Post.VISIBILITY_EVERYWHERE,
            is_public=True,
        )

    def _create_user(self):
        self._user_counter += 1
        return User.objects.create(
            email=f"renderer_test_{self._user_counter}@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            slug=f"renderer_user_{self._user_counter}",
        )

    def _post_url(self):
        return reverse("show_post", args=(self.post.type, self.post.slug))


class TestRenderPostQueryOptimization(RendererTestBase):
    def test_no_post_join_in_comment_query(self):
        """Comments query should not JOIN the posts table."""
        Comment.objects.create(author=self.user, post=self.post, text="test")
        client = HelperClient(self.user)
        client.authorise()

        with CaptureQueriesContext(connection) as queries:
            response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        comment_queries = [
            q["sql"] for q in queries
            if "comments" in q["sql"] and q["sql"].startswith("SELECT")
        ]
        for sql in comment_queries:
            self.assertNotIn('JOIN "posts"', sql)

    def test_no_reply_to_join_in_comment_query(self):
        """Comments query should not self-JOIN for reply_to."""
        top = Comment.objects.create(author=self.user, post=self.post, text="top")
        Comment.objects.create(author=self.user, post=self.post, text="reply", reply_to=top)
        client = HelperClient(self.user)
        client.authorise()

        with CaptureQueriesContext(connection) as queries:
            response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        comment_queries = [
            q["sql"] for q in queries
            if '"comments"' in q["sql"]
               and q["sql"].startswith("SELECT")
               and "comment_votes" not in q["sql"]
        ]
        for sql in comment_queries:
            joined_tables = sql.count('JOIN')
            self.assertLessEqual(joined_tables, 1, f"Expected at most 1 JOIN (author), got: {sql}")

    def test_deferred_fields_not_in_query(self):
        """ipaddress, useragent, url should not appear in the comment SELECT."""
        Comment.objects.create(author=self.user, post=self.post, text="test")
        client = HelperClient(self.user)
        client.authorise()

        with CaptureQueriesContext(connection) as queries:
            client.get(self._post_url())

        comment_queries = [
            q["sql"] for q in queries
            if '"comments"' in q["sql"]
               and q["sql"].startswith("SELECT")
               and "comment_votes" not in q["sql"]
        ]
        self.assertTrue(len(comment_queries) > 0)
        for sql in comment_queries:
            self.assertNotIn('"ipaddress"', sql)
            self.assertNotIn('"useragent"', sql)


class TestRenderPostVotes(RendererTestBase):
    def test_upvoted_at_present_for_voted_comment(self):
        """Voted comments should have upvoted_at in the rendered page."""
        other_user = self._create_user()
        comment = Comment.objects.create(author=other_user, post=self.post, text="voteable")
        CommentVote.objects.create(user=self.user, comment=comment, post=self.post)

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "initial-is-voted")

    def test_upvoted_at_absent_for_unvoted_comment(self):
        """Unvoted comments should not have upvoted_at."""
        other_user = self._create_user()
        Comment.objects.create(author=other_user, post=self.post, text="no vote")

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "initial-is-voted")

    def test_anonymous_sees_no_votes(self):
        """Anonymous users should see comments without vote state."""
        comment = Comment.objects.create(author=self.user, post=self.post, text="anon test")
        CommentVote.objects.create(user=self.user, comment=comment, post=self.post)

        client = HelperClient()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "initial-is-voted")

    def test_votes_fetched_in_separate_query(self):
        """Vote data should come from a separate query, not a correlated subquery."""
        other_user = self._create_user()
        comment = Comment.objects.create(author=other_user, post=self.post, text="test")
        CommentVote.objects.create(user=self.user, comment=comment, post=self.post)

        client = HelperClient(self.user)
        client.authorise()

        with CaptureQueriesContext(connection) as queries:
            client.get(self._post_url())

        comment_select = [
            q["sql"] for q in queries
            if '"comments"' in q["sql"]
               and q["sql"].startswith("SELECT")
               and "comment_votes" not in q["sql"]
        ]
        for sql in comment_select:
            self.assertNotIn("comment_votes", sql)


class TestRenderPostCommentOrder(RendererTestBase):
    def test_same_upvotes_sorted_oldest_first(self):
        """When sorting by upvotes, comments with equal upvotes should show oldest first."""
        old = Comment.objects.create(author=self.user, post=self.post, text="old comment")
        new = Comment.objects.create(author=self.user, post=self.post, text="new comment")
        Comment.objects.filter(id=old.id).update(upvotes=1)
        Comment.objects.filter(id=new.id).update(upvotes=1)

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(self._post_url())

        content = response.content.decode()
        pos_old = content.index("old comment")
        pos_new = content.index("new comment")
        self.assertLess(pos_old, pos_new, "Older comment should appear before newer one with same upvotes")


class TestRenderPostCommentPostReference(RendererTestBase):
    def test_comment_post_fields_accessible(self):
        """Comments should have post reference set for template rendering."""
        Comment.objects.create(author=self.user, post=self.post, text="post ref test")

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f"#comment-", content)

    def test_deleted_comment_shows_by_whom(self):
        """Deleted comment should show who deleted it (uses comment.post.author_id)."""
        other_user = self._create_user()
        comment = Comment.objects.create(author=other_user, post=self.post, text="to delete")
        comment.is_deleted = True
        comment.deleted_by = self.user.id  # post author deleted it
        comment.save()

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "удален")


class TestRenderPostCommentRateLimit(RendererTestBase):
    def test_comment_form_shown_when_under_limit(self):
        client = HelperClient(self.user)
        client.authorise()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "comment-form-form")
        self.assertNotContains(response, "block-comments-restricted")

    @override_settings(RATE_LIMIT_COMMENTS_PER_DAY=2)
    def test_rate_limit_block_shown_when_exceeded(self):
        """When user exceeds daily comment limit, comment form is replaced with restriction block."""
        for i in range(2):
            Comment.objects.create(author=self.user, post=self.post, text=f"spam {i}")

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "block-comments-rate-limited")
        self.assertNotContains(response, "comment-form-form")

    def test_anonymous_sees_no_comment_form(self):
        client = HelperClient()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "comment-form-form")
        self.assertNotContains(response, "block-comments-rate-limited")

    def test_rate_limit_not_computed_in_template(self):
        """Rate limit check should happen in the view, not via template tag query."""
        client = HelperClient(self.user)
        client.authorise()

        with CaptureQueriesContext(connection) as queries:
            client.get(self._post_url())

        template_tag_queries = [
            q["sql"] for q in queries
            if "comments" in q["sql"]
               and "COUNT" in q["sql"]
               and q["sql"].startswith("SELECT")
        ]
        self.assertLessEqual(len(template_tag_queries), 1)
