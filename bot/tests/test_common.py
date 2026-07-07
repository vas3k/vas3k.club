import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from django.test import SimpleTestCase

from bot.handlers.common import get_club_comment, get_club_post


class TestBotCommonHelpers(SimpleTestCase):
    def test_get_club_post_parses_reply_link(self):
        post = SimpleNamespace(slug="bot-post", is_commentable=True)
        mock_queryset = MagicMock()
        mock_queryset.first.return_value = post
        bot_filter = MagicMock(return_value=mock_queryset)
        update = SimpleNamespace(
            message=SimpleNamespace(
                reply_to_message=SimpleNamespace(
                    entities=[SimpleNamespace(type="text_link", url="https://vas3k.club/post/bot-post/")],
                    caption_entities=[],
                ),
                reply_text=AsyncMock(),
            )
        )

        with patch("bot.handlers.common.Post.objects.filter", bot_filter):
            result = asyncio.run(get_club_post(update))

        self.assertEqual(result.slug, post.slug)
        update.message.reply_text.assert_not_called()

    def test_get_club_comment_replies_if_comment_missing(self):
        missing_comment_id = str(uuid4())
        mock_queryset = MagicMock()
        mock_queryset.first.return_value = None
        comment_filter = MagicMock(return_value=mock_queryset)
        update = SimpleNamespace(
            message=SimpleNamespace(
                reply_to_message=SimpleNamespace(
                    entities=[
                        SimpleNamespace(
                            type="text_link",
                            url=f"https://vas3k.club/post/some-post/#comment-{missing_comment_id}",
                        )
                    ],
                    caption_entities=[],
                ),
                reply_text=AsyncMock(),
            )
        )

        with patch("bot.handlers.common.Comment.objects.filter", comment_filter):
            result = asyncio.run(get_club_comment(update))

        self.assertIsNone(result)
        update.message.reply_text.assert_awaited_once()
