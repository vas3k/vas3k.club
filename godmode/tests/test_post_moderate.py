from unittest.mock import patch

from django.test import RequestFactory, TestCase

from debug.utils_for_tests import create_approved_user
from godmode.actions.post_moderate import post_moderate_action
from notifications.telegram.posts import notify_post_rejected
from posts.models.post import Post
from users.models.user import User


class TestPostModerationText(TestCase):
    def setUp(self):
        self.author = create_approved_user("moderation_text_author", telegram_id="123")
        self.moderator = create_approved_user("moderation_text_moderator", roles=[User.ROLE_MODERATOR])
        self.post = Post.objects.create(
            author=self.author, title='<script>alert("title")</script>', text="Content",
            moderation_status=Post.MODERATION_PENDING, visibility=Post.VISIBILITY_LINK_ONLY,
        )

    def test_custom_rejection_is_stored_escaped_and_sent_unchanged(self):
        custom_reason = '<script>alert("reason")</script> & details'
        request = RequestFactory().post("/", {"reason": "custom", "custom_reason": custom_reason})
        request.me = self.moderator

        with (
            patch("godmode.actions.post_moderate.async_task") as enqueue,
            patch("godmode.actions.post_moderate.SearchIndex.update_post_index"),
            patch("godmode.actions.post_moderate.render"),
        ):
            post_moderate_action(request, self.post)

        self.post.refresh_from_db()
        data = self.post.moderation_data
        self.assertEqual(set(data), {"reason", "text", "user"})
        self.assertEqual(data["reason"], "custom")
        self.assertEqual(data["user"]["slug"], self.moderator.slug)
        self.assertNotIn("<script>", data["text"])
        self.assertIn("&lt;script&gt;", data["text"])
        self.assertIn("&amp; details", data["text"])
        self.assertEqual(self.post.visibility, Post.VISIBILITY_DRAFT)
        self.assertEqual(self.post.moderation_status, Post.MODERATION_REJECTED)
        enqueue.assert_called_once_with(notify_post_rejected, self.post)

        with patch("notifications.telegram.posts.send_telegram_message") as send:
            notify_post_rejected(self.post)

        self.assertEqual(send.call_args.kwargs["text"], data["text"])

    def test_predefined_rejection_stores_rendered_snapshot(self):
        request = RequestFactory().post("/", {"reason": "title"})
        request.me = self.moderator

        with (
            patch("godmode.actions.post_moderate.render_to_string", return_value="Rendered rejection"),
            patch("godmode.actions.post_moderate.async_task"),
            patch("godmode.actions.post_moderate.SearchIndex.update_post_index"),
            patch("godmode.actions.post_moderate.render"),
        ):
            post_moderate_action(request, self.post)

        self.post.refresh_from_db()
        self.assertEqual(set(self.post.moderation_data), {"reason", "text", "user"})
        self.assertEqual(self.post.moderation_data["reason"], "title")
        self.assertEqual(self.post.moderation_data["text"], "Rendered rejection")

    def test_blank_custom_reason_does_not_reject(self):
        request = RequestFactory().post("/", {"reason": "custom", "custom_reason": "  "})
        request.me = self.moderator

        with (
            patch("godmode.actions.post_moderate.render"),
            patch("godmode.actions.post_moderate.async_task") as enqueue,
        ):
            post_moderate_action(request, self.post)

        self.post.refresh_from_db()
        self.assertEqual(self.post.moderation_status, Post.MODERATION_PENDING)
        self.assertIsNone(self.post.moderation_data)
        enqueue.assert_not_called()
