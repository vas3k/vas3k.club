import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from django.test import TransactionTestCase, override_settings

from bot.handlers.moderation import reject_post
from debug.utils_for_tests import create_approved_user
from posts.models.post import Post
from users.models.user import User


class TestPostRejectionAttribution(TransactionTestCase):
    @override_settings(TELEGRAM_ADMIN_CHAT_ID="123")
    def test_reject_post_records_authenticated_moderator(self):
        author = create_approved_user("rejection_author")
        moderator = create_approved_user("rejecting_moderator", roles=[User.ROLE_MODERATOR], telegram_id="456")
        post = Post.objects.create(
            slug="post_to_reject", author=author, title="Post", text="Content",
            visibility=Post.VISIBILITY_LINK_ONLY, moderation_status=Post.MODERATION_PENDING,
        )
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=456, full_name="Moderator"),
            effective_chat=SimpleNamespace(id=123, send_message=AsyncMock()),
            callback_query=SimpleNamespace(
                data=f"reject_post_title:{post.id}", edit_message_reply_markup=AsyncMock(),
            ),
        )
        with (
            patch.dict("os.environ", {"DJANGO_ALLOW_ASYNC_UNSAFE": "true"}),
            patch("bot.handlers.moderation.async_task") as enqueue,
            patch("bot.handlers.moderation.SearchIndex.update_post_index"),
            patch("bot.handlers.moderation.render_to_string", return_value="Rendered rejection"),
        ):
            asyncio.run(reject_post(update, None))

        post.refresh_from_db()
        self.assertEqual(post.moderation_data, {
            "reason": "title",
            "text": "Rendered rejection",
            "user": {
                "slug": moderator.slug,
                "avatar": moderator.get_avatar(),
                "full_name": moderator.full_name,
            },
        })
        self.assertEqual(post.moderation_status, Post.MODERATION_REJECTED)
        self.assertEqual(post.visibility, Post.VISIBILITY_DRAFT)
        enqueue.assert_called_once()
