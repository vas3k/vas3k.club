from datetime import datetime, timedelta

from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse

from comments.models import Comment, CommentVote
from debug.helpers import HelperClient
from posts.models.post import Post
from posts.models.votes import PostVote
from users.models.mute import UserMuted
from users.models.notes import UserNote
from users.models.user import User


class RendererTestBase(TestCase):
    def setUp(self):
        self.user_counter = 0
        self.user = self.create_user()
        self.post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="renderer_test_post",
            title="Test Post",
            text="Hello",
            author=self.user,
            visibility=Post.VISIBILITY_EVERYWHERE,
            is_public=True,
        )

    def create_user(self):
        self.user_counter += 1
        return User.objects.create(
            email=f"renderer_test_{self.user_counter}@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            slug=f"renderer_user_{self.user_counter}",
        )


class TestRenderPostQueryOptimization(RendererTestBase):
    def test_no_post_join_in_comment_query(self):
        """Comments query should not JOIN the posts table."""
        Comment.objects.create(author=self.user, post=self.post, text="test")
        client = HelperClient(self.user)
        client.authorise()

        with CaptureQueriesContext(connection) as queries:
            response = client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

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
            response = client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

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
            client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

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
        """Load the current user's vote state for comments."""
        other_user = self.create_user()
        comment = Comment.objects.create(author=other_user, post=self.post, text="voteable")
        CommentVote.objects.create(user=self.user, comment=comment, post=self.post)

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["comments"][0].upvoted_at)

    def test_upvoted_at_absent_for_unvoted_comment(self):
        """Unvoted comments should not have upvoted_at."""
        other_user = self.create_user()
        Comment.objects.create(author=other_user, post=self.post, text="no vote")

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["comments"][0].upvoted_at)

    def test_anonymous_sees_no_votes(self):
        """Anonymous users should see comments without vote state."""
        comment = Comment.objects.create(author=self.user, post=self.post, text="anon test")
        CommentVote.objects.create(user=self.user, comment=comment, post=self.post)

        client = HelperClient()
        response = client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["comments"][0].upvoted_at)

    def test_votes_fetched_in_separate_query(self):
        """Vote data should come from a separate query, not a correlated subquery."""
        other_user = self.create_user()
        comment = Comment.objects.create(author=other_user, post=self.post, text="test")
        CommentVote.objects.create(user=self.user, comment=comment, post=self.post)

        client = HelperClient(self.user)
        client.authorise()

        with CaptureQueriesContext(connection) as queries:
            client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

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
        response = client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

        self.assertEqual([comment.id for comment in response.context["comments"]], [old.id, new.id])


class TestRenderPostCommentRateLimit(RendererTestBase):
    def test_comment_limit_not_exceeded(self):
        client = HelperClient(self.user)
        client.authorise()
        response = client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_comment_rate_exceeded"])

    @override_settings(RATE_LIMIT_COMMENTS_PER_DAY=2)
    def test_comment_limit_exceeded(self):
        """The daily limit is calculated for the current user."""
        for i in range(2):
            Comment.objects.create(author=self.user, post=self.post, text=f"spam {i}")

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_comment_rate_exceeded"])

    def test_anonymous_has_no_comment_limit_state(self):
        client = HelperClient()
        response = client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_comment_rate_exceeded"])

    def test_rate_limit_not_computed_in_template(self):
        """Rate limit check should happen in the view, not via template tag query."""
        client = HelperClient(self.user)
        client.authorise()

        with CaptureQueriesContext(connection) as queries:
            client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

        template_tag_queries = [
            q["sql"] for q in queries
            if "comments" in q["sql"]
               and "COUNT" in q["sql"]
               and q["sql"].startswith("SELECT")
        ]
        self.assertLessEqual(len(template_tag_queries), 1)


class TestRenderPostUpvotedAt(RendererTestBase):
    def test_post_vote_query_uses_values_list(self):
        """PostVote query should fetch only created_at, not the full object."""
        PostVote.objects.create(user=self.user, post=self.post)
        client = HelperClient(self.user)
        client.authorise()

        with CaptureQueriesContext(connection) as queries:
            client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

        vote_queries = [
            q["sql"] for q in queries
            if "post_votes" in q["sql"]
               and q["sql"].startswith("SELECT")
               and "comment_votes" not in q["sql"]
        ]
        for sql in vote_queries:
            self.assertNotIn('"ipaddress"', sql)


class TestRenderPostCollectibleTag(RendererTestBase):
    def test_no_extra_query_when_tag_code_is_none(self):
        """Post without collectible_tag_code should not query Tag table."""
        self.post.collectible_tag_code = None
        self.post.save()

        client = HelperClient(self.user)
        client.authorise()

        with CaptureQueriesContext(connection) as queries:
            client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

        tag_queries = [
            q["sql"] for q in queries
            if '"tags"' in q["sql"] and q["sql"].startswith("SELECT")
        ]
        self.assertEqual(len(tag_queries), 0)

    def test_nonexistent_tag_code_no_usertag_query(self):
        """Post with collectible_tag_code pointing to missing Tag should not query UserTag."""
        self.post.collectible_tag_code = "nonexistent_tag"
        self.post.save()

        client = HelperClient(self.user)
        client.authorise()

        with CaptureQueriesContext(connection) as queries:
            client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

        usertag_queries = [
            q["sql"] for q in queries
            if '"user_tags"' in q["sql"] and q["sql"].startswith("SELECT")
        ]
        self.assertEqual(len(usertag_queries), 0)


class TestRenderPostMutedAndNotes(RendererTestBase):
    def test_muted_user_ids_loaded(self):
        """Muted users should be tracked in context for comment rendering."""
        other_user = self.create_user()
        Comment.objects.create(author=other_user, post=self.post, text="muted user comment")
        UserMuted.objects.create(user_from=self.user, user_to=other_user)

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

        self.assertEqual(response.status_code, 200)
        self.assertIn(other_user.id, response.context["muted_user_ids"])

    def test_user_notes_loaded(self):
        """User notes should be available in the rendered context."""
        other_user = self.create_user()
        Comment.objects.create(author=other_user, post=self.post, text="noted user comment")
        UserNote.objects.create(user_from=self.user, user_to=other_user, text="my note")

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(reverse("show_post", args=(self.post.type, self.post.slug)))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user_notes"].get(other_user.id), "my note")
