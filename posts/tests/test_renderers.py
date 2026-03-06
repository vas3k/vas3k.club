from datetime import datetime, timedelta

from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse

from comments.models import Comment, CommentVote
from debug.helpers import HelperClient
from posts.models.post import Post
from bookmarks.models import PostBookmark
from posts.models.votes import PostVote
from tags.models import Tag, UserTag
from users.models.mute import UserMuted
from users.models.notes import UserNote
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


class TestRenderPostUpvotedAt(RendererTestBase):
    def test_post_upvote_timestamp_in_response(self):
        """Post upvoted_at should appear as initial-upvote-timestamp in rendered page."""
        PostVote.objects.create(user=self.user, post=self.post)

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "initial-upvote-timestamp=")

    def test_no_post_upvote_no_timestamp(self):
        """Without a post vote, initial-upvote-timestamp should not appear."""
        client = HelperClient(self.user)
        client.authorise()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "initial-upvote-timestamp=")

    def test_post_vote_query_uses_values_list(self):
        """PostVote query should fetch only created_at, not the full object."""
        PostVote.objects.create(user=self.user, post=self.post)
        client = HelperClient(self.user)
        client.authorise()

        with CaptureQueriesContext(connection) as queries:
            client.get(self._post_url())

        vote_queries = [
            q["sql"] for q in queries
            if "post_votes" in q["sql"]
               and q["sql"].startswith("SELECT")
               and "comment_votes" not in q["sql"]
        ]
        for sql in vote_queries:
            self.assertNotIn('"ipaddress"', sql)


class TestRenderPostBookmark(RendererTestBase):
    def test_bookmark_state_for_bookmarked_post(self):
        PostBookmark.objects.create(user=self.user, post=self.post)

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "initial-is-bookmarked")

    def test_no_bookmark_state_for_unbookmarked_post(self):
        client = HelperClient(self.user)
        client.authorise()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "initial-is-bookmarked")


class TestRenderPostCollectibleTag(RendererTestBase):
    def test_collectible_tag_rendered_when_exists(self):
        """Post with a valid collectible_tag_code should render the tag widget."""
        tag = Tag.objects.create(code="test_collect", name="Test Collectible", group=Tag.GROUP_COLLECTIBLE)
        self.post.collectible_tag_code = tag.code
        self.post.save()

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Collectible")

    def test_collected_tag_shows_active(self):
        """Collected tag should show active state for the user."""
        tag = Tag.objects.create(code="test_collected", name="Collected Tag", group=Tag.GROUP_COLLECTIBLE)
        UserTag.objects.create(user=self.user, tag=tag, name=tag.name)
        self.post.collectible_tag_code = tag.code
        self.post.save()

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "is-active-by-default")

    def test_no_extra_query_when_tag_code_is_none(self):
        """Post without collectible_tag_code should not query Tag table."""
        self.post.collectible_tag_code = None
        self.post.save()

        client = HelperClient(self.user)
        client.authorise()

        with CaptureQueriesContext(connection) as queries:
            client.get(self._post_url())

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
            client.get(self._post_url())

        usertag_queries = [
            q["sql"] for q in queries
            if '"user_tags"' in q["sql"] and q["sql"].startswith("SELECT")
        ]
        self.assertEqual(len(usertag_queries), 0)


class TestRenderPostMutedAndNotes(RendererTestBase):
    def test_muted_user_ids_loaded(self):
        """Muted users should be tracked in context for comment rendering."""
        other_user = self._create_user()
        Comment.objects.create(author=other_user, post=self.post, text="muted user comment")
        UserMuted.objects.create(user_from=self.user, user_to=other_user)

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        self.assertIn(other_user.id, response.context["muted_user_ids"])

    def test_user_notes_loaded(self):
        """User notes should be available in the rendered context."""
        other_user = self._create_user()
        Comment.objects.create(author=other_user, post=self.post, text="noted user comment")
        UserNote.objects.create(user_from=self.user, user_to=other_user, text="my note")

        client = HelperClient(self.user)
        client.authorise()
        response = client.get(self._post_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user_notes"].get(other_user.id), "my note")
