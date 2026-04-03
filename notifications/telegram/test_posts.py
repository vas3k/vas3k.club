from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase

from notifications.telegram.common import Chat
from notifications.telegram.posts import (
    announce_in_club_chats,
    announce_in_club_channel,
    notify_post_approved,
    notify_post_rejected,
    send_intro_changes_to_moderators,
    send_published_post_to_moderators,
)
from posts.models.post import Post
from rooms.models import Room
from users.models.user import User


def _create_user(slug, telegram_id="123456", **kwargs):
    return User.objects.create(
        email=f"{slug}@xx.com",
        membership_started_at=datetime.now() - timedelta(days=5),
        membership_expires_at=datetime.now() + timedelta(days=5),
        moderation_status=User.MODERATION_STATUS_APPROVED,
        slug=slug,
        telegram_id=telegram_id,
        **kwargs,
    )


def _create_post(author, **kwargs):
    defaults = dict(
        type=Post.TYPE_POST,
        slug="test-post",
        title="Test Post",
        text="body",
        visibility=Post.VISIBILITY_EVERYWHERE,
    )
    defaults.update(kwargs)
    return Post.objects.create(author=author, **defaults)


class TestNotifyPostApproved(TestCase):
    def setUp(self):
        self.author = _create_user("approved_author")
        self.post = _create_post(self.author)

    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>approved</b>")
    def test_sends_notification_to_author(self, mock_render, mock_send):
        notify_post_approved(self.post)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        self.assertEqual(call_kwargs.kwargs["chat"].id, self.author.telegram_id)

    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>approved</b>")
    def test_uses_standard_template_for_regular_post(self, mock_render, mock_send):
        notify_post_approved(self.post)

        mock_render.assert_called_once_with("post_approved.html", post=self.post)

    @patch("notifications.telegram.posts.send_telegram_message")
    def test_skips_author_without_telegram(self, mock_send):
        self.author.telegram_id = None
        self.author.save()

        notify_post_approved(self.post)

        mock_send.assert_not_called()

    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>room</b>")
    def test_uses_room_template_for_room_only_post(self, mock_render, mock_send):
        room = Room.objects.create(slug="test-room", title="Test Room")
        self.post.room = room
        self.post.is_room_only = True
        self.post.save()

        notify_post_approved(self.post)

        mock_render.assert_called_once_with("post_approved_in_room.html", post=self.post)


class TestNotifyPostRejected(TestCase):
    def setUp(self):
        self.author = _create_user("rejected_author")
        self.post = _create_post(self.author, slug="rejected-post")

    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>rejected</b>")
    def test_sends_rejection_to_author(self, mock_render, mock_send):
        from bot.handlers.common import PostRejectReason
        notify_post_rejected(self.post, PostRejectReason.draft)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        self.assertEqual(call_kwargs.kwargs["chat"].id, self.author.telegram_id)

    @patch("notifications.telegram.posts.send_telegram_message")
    def test_skips_author_without_telegram(self, mock_send):
        self.author.telegram_id = None
        self.author.save()

        from bot.handlers.common import PostRejectReason
        notify_post_rejected(self.post, PostRejectReason.draft)

        mock_send.assert_not_called()

    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message")
    def test_falls_back_to_draft_template_on_missing_template(self, mock_render, mock_send):
        from django.template import TemplateDoesNotExist
        from bot.handlers.common import PostRejectReason

        mock_render.side_effect = [TemplateDoesNotExist("missing"), "<b>fallback</b>"]

        notify_post_rejected(self.post, PostRejectReason.draft)

        self.assertEqual(mock_render.call_count, 2)
        self.assertEqual(mock_render.call_args_list[1].args[0], "post_rejected/draft.html")


class TestAnnounceInClubChats(TestCase):
    def setUp(self):
        self.author = _create_user("chat_author")

    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>announce</b>")
    def test_announces_public_post_to_club_chat(self, mock_render, mock_send):
        post = _create_post(self.author, slug="public-post")

        announce_in_club_chats(post)

        mock_send.assert_called_once()

    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>announce</b>")
    def test_announces_to_room_chat_when_configured(self, mock_render, mock_send):
        room = Room.objects.create(
            slug="announce-room",
            title="Announce Room",
            chat_id="99999",
            send_new_posts_to_chat=True,
        )
        post = _create_post(self.author, slug="room-post", room=room)

        announce_in_club_chats(post)

        self.assertEqual(mock_send.call_count, 2)

    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>announce</b>")
    def test_skips_room_chat_when_disabled(self, mock_render, mock_send):
        room = Room.objects.create(
            slug="silent-room",
            title="Silent Room",
            chat_id="88888",
            send_new_posts_to_chat=False,
        )
        post = _create_post(self.author, slug="silent-post", room=room)

        announce_in_club_chats(post)

        mock_send.assert_called_once()


class TestAnnounceInClubChannel(TestCase):
    def setUp(self):
        self.author = _create_user("channel_author")
        self.post = _create_post(self.author, slug="channel-post")

    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>announce</b>")
    def test_sends_text_announcement(self, mock_render, mock_send):
        announce_in_club_channel(self.post)

        mock_send.assert_called_once()

    @patch("notifications.telegram.posts.send_telegram_image")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>announce</b>")
    def test_sends_image_when_provided(self, mock_render, mock_send_image):
        announce_in_club_channel(self.post, image="https://example.com/img.jpg")

        mock_send_image.assert_called_once()

    @patch("notifications.telegram.posts.send_telegram_message")
    def test_uses_custom_announce_text(self, mock_send):
        announce_in_club_channel(self.post, announce_text="Custom text")

        call_kwargs = mock_send.call_args.kwargs
        self.assertEqual(call_kwargs["text"], "Custom text")


class TestSendIntroChangesToModerators(TestCase):
    def setUp(self):
        self.author = _create_user("intro_author")

    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>intro</b>")
    def test_sends_for_intro_post(self, mock_render, mock_send):
        intro = _create_post(self.author, slug="intro-post", type=Post.TYPE_INTRO)

        send_intro_changes_to_moderators(intro)

        mock_send.assert_called_once()

    @patch("notifications.telegram.posts.send_telegram_message")
    def test_skips_non_intro_post(self, mock_send):
        post = _create_post(self.author, slug="regular-post", type=Post.TYPE_POST)

        send_intro_changes_to_moderators(post)

        mock_send.assert_not_called()


class TestSendPublishedPostToModerators(TestCase):
    def setUp(self):
        self.author = _create_user("mod_author")
        self.post = _create_post(self.author, slug="mod-post")

    @patch("notifications.telegram.posts.ai_rate_post_quality", return_value="<b>AI review</b>")
    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>review</b>")
    def test_sends_post_and_ai_review_to_moderators(self, mock_render, mock_send, mock_ai):
        mock_message = MagicMock()
        mock_message.message_id = 42
        mock_send.return_value = mock_message

        send_published_post_to_moderators(self.post)

        self.assertEqual(mock_send.call_count, 2)
        second_call = mock_send.call_args_list[1].kwargs
        self.assertEqual(second_call["reply_to_message_id"], 42)

    @patch("notifications.telegram.posts.ai_rate_post_quality", return_value="<b>AI review</b>")
    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>review</b>")
    def test_first_message_has_moderation_buttons(self, mock_render, mock_send, mock_ai):
        mock_message = MagicMock()
        mock_message.message_id = 1
        mock_send.return_value = mock_message

        send_published_post_to_moderators(self.post)

        first_call = mock_send.call_args_list[0]
        reply_markup = first_call.kwargs.get("reply_markup")
        self.assertIsNotNone(reply_markup)

        callbacks = [
            btn.callback_data
            for row in reply_markup.inline_keyboard
            for btn in row
            if btn.callback_data
        ]
        self.assertTrue(any(cb.startswith("approve_post:") for cb in callbacks))
        self.assertTrue(any(cb.startswith("reject_post:") for cb in callbacks))

