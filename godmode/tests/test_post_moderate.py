import json
from datetime import datetime
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.urls import reverse

from debug.utils_for_tests import create_approved_user, login
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
        self.assertEqual(set(data), {"reason", "text", "moderator", "moderated_at"})
        self.assertEqual(data["reason"], "custom")
        self.assertEqual(data["moderator"]["slug"], self.moderator.slug)
        self.assertRegex(data["moderated_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
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
        self.post.moderation_data = {"message_id": 42}
        self.post.save(update_fields=["moderation_data"])
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
        self.assertEqual(
            set(self.post.moderation_data),
            {"reason", "text", "moderator", "moderated_at", "message_id"},
        )
        self.assertEqual(self.post.moderation_data["reason"], "title")
        self.assertEqual(self.post.moderation_data["text"], "Rendered rejection")
        self.assertEqual(self.post.moderation_data["moderator"]["slug"], self.moderator.slug)
        self.assertEqual(self.post.moderation_data["message_id"], 42)

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

    def test_repeated_rejection_records_new_decision_and_sends_notifications(self):
        recorded = {
            "moderator": {"slug": "original-moderator"},
            "moderated_at": "2020-01-01T12:00:00Z",
            "reason": "title",
            "text": "Original rejection",
            "message_id": 42,
        }
        self.post.moderation_status = Post.MODERATION_REJECTED
        self.post.moderation_data = recorded
        self.post.save()
        request = RequestFactory().post("/", {"reason": "custom", "custom_reason": "Another reason"})
        request.me = self.moderator

        with (
            patch("godmode.actions.post_moderate.render"),
            patch("godmode.actions.post_moderate.async_task") as enqueue,
            patch("godmode.actions.post_moderate.SearchIndex.update_post_index") as update_index,
            patch("godmode.actions.post_moderate.send_telegram_message") as send,
        ):
            post_moderate_action(request, self.post)

        self.post.refresh_from_db()
        data = self.post.moderation_data
        self.assertEqual(data["moderator"]["slug"], self.moderator.slug)
        self.assertNotEqual(data["moderated_at"], recorded["moderated_at"])
        self.assertRegex(data["moderated_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(data["reason"], "custom")
        self.assertEqual(data["message_id"], 42)
        self.assertEqual(self.post.moderation_status, Post.MODERATION_REJECTED)
        self.assertEqual(self.post.visibility, Post.VISIBILITY_DRAFT)
        enqueue.assert_called_once_with(notify_post_rejected, self.post)
        update_index.assert_called_once_with(self.post)
        send.assert_called_once()


class TestGodmodeStatusChangeAttribution(TestCase):
    def setUp(self):
        self.author = create_approved_user("godmode_status_author")
        self.moderator = create_approved_user("godmode_status_moderator", roles=[User.ROLE_MODERATOR])
        self.post = Post.objects.create(
            author=self.author, title="Pending", text="Content",
            moderation_status=Post.MODERATION_PENDING, visibility=Post.VISIBILITY_LINK_ONLY,
            moderation_data={"message_id": 9, "text": "old", "reason": "title"},
        )
        login(self.client, self.moderator)
        self.url = reverse("godmode_edit_model", kwargs={"model_name": "posts", "item_id": self.post.id})

    def post_status(self, status):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        data = {}

        for name in form.fields:
            value = form[name].value()

            if value is None or value is False or value == []:
                continue

            if isinstance(value, datetime):
                data[name] = value.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(value, dict):
                data[name] = json.dumps(value)
            elif isinstance(value, list):
                data[name] = ",".join(str(item) for item in value)
            elif value is True:
                data[name] = "on"
            else:
                data[name] = value

        data["moderation_data"] = "{}"
        data["moderation_status"] = status
        return self.client.post(self.url, data)

    def test_changing_status_records_moderator_and_repeat_save_does_not(self):
        response = self.post_status(Post.MODERATION_APPROVED)
        form_errors = response.context["form"].errors if response.context else ""
        self.assertEqual(response.status_code, 302, form_errors)

        self.post.refresh_from_db()
        self.assertEqual(self.post.moderation_status, Post.MODERATION_APPROVED)
        self.assertEqual(set(self.post.moderation_data), {"message_id", "moderator", "moderated_at"})
        self.assertEqual(self.post.moderation_data["moderator"]["slug"], self.moderator.slug)
        self.assertEqual(self.post.moderation_data["message_id"], 9)
        recorded_at = self.post.moderation_data["moderated_at"]

        with patch("posts.models.post.datetime", wraps=datetime) as clock:
            clock.utcnow.return_value = datetime(2000, 1, 1)
            response = self.post_status(Post.MODERATION_APPROVED)

        self.assertEqual(response.status_code, 302)
        self.post.refresh_from_db()
        self.assertEqual(self.post.moderation_data["moderated_at"], recorded_at)

    def test_forgiving_records_moderator_without_rejection_reason(self):
        response = self.post_status(Post.MODERATION_FORGIVEN)
        self.assertEqual(response.status_code, 302)
        self.post.refresh_from_db()
        self.assertEqual(set(self.post.moderation_data), {"message_id", "moderator", "moderated_at"})
        self.assertEqual(self.post.moderation_data["moderator"]["slug"], self.moderator.slug)
        self.assertEqual(self.post.moderation_data["message_id"], 9)
        self.assertRegex(self.post.moderation_data["moderated_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_rejecting_records_moderator_and_preserves_reason(self):
        response = self.post_status(Post.MODERATION_REJECTED)
        self.assertEqual(response.status_code, 302)
        self.post.refresh_from_db()
        self.assertEqual(self.post.moderation_data["moderator"]["slug"], self.moderator.slug)
        self.assertEqual(self.post.moderation_data["reason"], "title")
        self.assertEqual(self.post.moderation_data["text"], "old")
        self.assertEqual(self.post.moderation_data["message_id"], 9)
        self.assertRegex(self.post.moderation_data["moderated_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
