import asyncio
import re
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from django.test import TransactionTestCase, override_settings

from bot.handlers.moderation import approve_post, approve_user_profile, forgive_post, reject_post
from debug.utils_for_tests import create_approved_user
from posts.models.post import Post
from users.models.user import User

MODERATED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def moderator_snapshot(moderator):
    return {
        "slug": moderator.slug,
        "avatar": moderator.get_avatar(),
        "full_name": moderator.full_name,
    }


def callback_update(data):
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=456, full_name="Moderator"),
        effective_chat=SimpleNamespace(id=123, send_message=AsyncMock()),
        callback_query=SimpleNamespace(data=data, edit_message_reply_markup=AsyncMock()),
    )


class TestPostRejectionAttribution(TransactionTestCase):
    def setUp(self):
        self.author = create_approved_user("rejection_author")
        self.moderator = create_approved_user(
            "rejecting_moderator", roles=[User.ROLE_MODERATOR], telegram_id="456",
        )

    def create_pending_post(self, slug, **kwargs):
        return Post.objects.create(
            slug=slug, author=self.author, title="Post", text="Content",
            visibility=Post.VISIBILITY_LINK_ONLY, moderation_status=Post.MODERATION_PENDING,
            moderation_data={"message_id": 77}, **kwargs,
        )

    @override_settings(TELEGRAM_ADMIN_CHAT_ID="123")
    def test_reject_post_records_authenticated_moderator(self):
        post = self.create_pending_post("post_to_reject")
        with (
            patch.dict("os.environ", {"DJANGO_ALLOW_ASYNC_UNSAFE": "true"}),
            patch("bot.handlers.moderation.async_task") as enqueue,
            patch("bot.handlers.moderation.SearchIndex.update_post_index"),
            patch("bot.handlers.moderation.render_to_string", return_value="Rendered rejection"),
        ):
            asyncio.run(reject_post(callback_update(f"reject_post_title:{post.id}"), None))

        post.refresh_from_db()
        self.assertEqual(post.moderation_data["reason"], "title")
        self.assertEqual(post.moderation_data["text"], "Rendered rejection")
        self.assertEqual(post.moderation_data["moderator"], moderator_snapshot(self.moderator))
        self.assertRegex(post.moderation_data["moderated_at"], MODERATED_AT_RE)
        self.assertEqual(post.moderation_data["message_id"], 77)
        self.assertNotIn("user", post.moderation_data)
        self.assertEqual(post.moderation_status, Post.MODERATION_REJECTED)
        self.assertEqual(post.visibility, Post.VISIBILITY_DRAFT)
        enqueue.assert_called_once()

    @override_settings(TELEGRAM_ADMIN_CHAT_ID="123")
    def test_approve_and_forgive_record_moderator_without_reason(self):
        approved = self.create_pending_post("post_to_approve")
        forgiven = self.create_pending_post("post_to_forgive")
        with (
            patch.dict("os.environ", {"DJANGO_ALLOW_ASYNC_UNSAFE": "true"}),
            patch("bot.handlers.moderation.async_task"),
            patch("bot.handlers.moderation.SearchIndex.update_post_index"),
        ):
            asyncio.run(approve_post(callback_update(f"approve_post:{approved.id}"), None))
            asyncio.run(forgive_post(callback_update(f"forgive_post:{forgiven.id}"), None))

        approved.refresh_from_db()
        forgiven.refresh_from_db()

        for post, status in (
            (approved, Post.MODERATION_APPROVED),
            (forgiven, Post.MODERATION_FORGIVEN),
        ):
            self.assertEqual(post.moderation_status, status)
            self.assertEqual(set(post.moderation_data), {"moderator", "moderated_at", "message_id"})
            self.assertEqual(post.moderation_data["moderator"], moderator_snapshot(self.moderator))
            self.assertRegex(post.moderation_data["moderated_at"], MODERATED_AT_RE)
            self.assertEqual(post.moderation_data["message_id"], 77)

    @override_settings(TELEGRAM_ADMIN_CHAT_ID="123")
    def test_repeated_decision_does_not_overwrite_attribution(self):
        for handler, code in (
            (approve_post, "approve_post"),
            (forgive_post, "forgive_post"),
            (reject_post, "reject_post_title"),
        ):
            with self.subTest(code=code):
                post = self.create_pending_post(f"{code}_twice")

                with (
                    patch.dict("os.environ", {"DJANGO_ALLOW_ASYNC_UNSAFE": "true"}),
                    patch("bot.handlers.moderation.async_task") as enqueue,
                    patch("bot.handlers.moderation.SearchIndex.update_post_index") as update_index,
                    patch("posts.models.post.datetime", wraps=datetime) as clock,
                ):
                    clock.utcnow.return_value = datetime(2026, 1, 1)
                    asyncio.run(handler(callback_update(f"{code}:{post.id}"), None))
                    post.refresh_from_db()
                    recorded = post.moderation_data
                    status = post.moderation_status
                    enqueue.reset_mock()
                    update_index.reset_mock()
                    clock.utcnow.return_value = datetime(2026, 1, 2)
                    asyncio.run(handler(callback_update(f"{code}:{post.id}"), None))

                post.refresh_from_db()
                self.assertEqual(post.moderation_data, recorded)
                self.assertEqual(post.moderation_status, status)
                enqueue.assert_not_called()
                update_index.assert_not_called()

    @override_settings(TELEGRAM_ADMIN_CHAT_ID="123")
    def test_approving_profile_records_intro_moderator(self):
        candidate = create_approved_user("intro_candidate")
        candidate.moderation_status = User.MODERATION_STATUS_ON_REVIEW
        candidate.save(update_fields=["moderation_status"])
        intro = Post.objects.create(
            slug="intro-candidate", author=candidate, type=Post.TYPE_INTRO,
            title="intro", text="hello", moderation_status=Post.MODERATION_PENDING,
        )
        with (
            patch.dict("os.environ", {"DJANGO_ALLOW_ASYNC_UNSAFE": "true"}),
            patch("bot.handlers.moderation.async_task"),
            patch("bot.handlers.moderation.SearchIndex.update_user_index"),
            patch("bot.handlers.moderation.send_welcome_drink"),
        ):
            asyncio.run(approve_user_profile(callback_update(f"approve_user:{candidate.id}"), None))

        intro.refresh_from_db()
        self.assertEqual(intro.moderation_status, Post.MODERATION_APPROVED)
        self.assertEqual(set(intro.moderation_data), {"moderator", "moderated_at"})
        self.assertEqual(intro.moderation_data["moderator"], moderator_snapshot(self.moderator))
        self.assertRegex(intro.moderation_data["moderated_at"], MODERATED_AT_RE)
