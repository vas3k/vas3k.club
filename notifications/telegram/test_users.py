from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase

from notifications.telegram.users import (
    notify_profile_needs_review,
    notify_user_profile_approved,
    notify_user_profile_rejected,
    notify_user_ping,
    notify_admin_user_ping,
    notify_user_auth,
)
from bot.handlers.common import UserRejectReason
from posts.models.post import Post
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


class TestNotifyProfileNeedsReview(TestCase):
    @patch("notifications.telegram.users.ai_rate_intro_quality", return_value="<b>AI intro review</b>")
    @patch("notifications.telegram.users.send_telegram_message")
    @patch("notifications.telegram.users.render_html_message", return_value="<b>review</b>")
    def test_sends_review_and_ai_rating_to_moderators(self, mock_render, mock_send, mock_ai):
        user = _create_user("needs_review")
        intro = Post.objects.create(
            type=Post.TYPE_INTRO,
            slug="review-intro",
            title="Intro",
            text="Hello",
            author=user,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )

        mock_message = MagicMock()
        mock_message.message_id = 99
        mock_send.return_value = mock_message

        notify_profile_needs_review(user, intro)

        self.assertEqual(mock_send.call_count, 2)
        second_call = mock_send.call_args_list[1].kwargs
        self.assertEqual(second_call["reply_to_message_id"], 99)

    @patch("notifications.telegram.users.ai_rate_intro_quality", return_value="<b>AI</b>")
    @patch("notifications.telegram.users.send_telegram_message")
    @patch("notifications.telegram.users.render_html_message", return_value="<b>review</b>")
    def test_first_message_has_moderation_buttons(self, mock_render, mock_send, mock_ai):
        user = _create_user("review_buttons")
        intro = Post.objects.create(
            type=Post.TYPE_INTRO,
            slug="review-buttons-intro",
            title="Intro",
            text="Hello",
            author=user,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )

        mock_message = MagicMock()
        mock_message.message_id = 1
        mock_send.return_value = mock_message

        notify_profile_needs_review(user, intro)

        first_call = mock_send.call_args_list[0]
        reply_markup = first_call.kwargs.get("reply_markup")
        self.assertIsNotNone(reply_markup)

        callbacks = [
            btn.callback_data
            for row in reply_markup.inline_keyboard
            for btn in row
            if btn.callback_data
        ]
        self.assertTrue(any(cb.startswith("approve_user:") for cb in callbacks))
        self.assertTrue(any(cb.startswith("reject_user_intro:") for cb in callbacks))


class TestNotifyUserProfileApproved(TestCase):
    @patch("notifications.telegram.users.send_telegram_message")
    def test_sends_welcome_to_user(self, mock_send):
        user = _create_user("approved_user")

        notify_user_profile_approved(user)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        self.assertEqual(call_kwargs["chat"].id, user.telegram_id)
        self.assertIn("Поздравляем", call_kwargs["text"])

    @patch("notifications.telegram.users.send_telegram_message")
    def test_skips_user_without_telegram(self, mock_send):
        user = _create_user("no_tg_approved", telegram_id=None)

        notify_user_profile_approved(user)

        mock_send.assert_not_called()


class TestNotifyUserProfileRejected(TestCase):
    @patch("notifications.telegram.users.send_telegram_message")
    @patch("notifications.telegram.users.render_html_message", return_value="<b>rejected</b>")
    def test_sends_rejection_to_user(self, mock_render, mock_send):
        user = _create_user("rejected_user")

        notify_user_profile_rejected(user, UserRejectReason.intro)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        self.assertEqual(call_kwargs["chat"].id, user.telegram_id)

    @patch("notifications.telegram.users.send_telegram_message")
    def test_skips_user_without_telegram(self, mock_send):
        user = _create_user("no_tg_rejected", telegram_id=None)

        notify_user_profile_rejected(user, UserRejectReason.intro)

        mock_send.assert_not_called()

    @patch("notifications.telegram.users.send_telegram_message")
    @patch("notifications.telegram.users.render_html_message")
    def test_falls_back_to_intro_template(self, mock_render, mock_send):
        from django.template import TemplateDoesNotExist

        user = _create_user("fallback_rejected")
        mock_render.side_effect = [TemplateDoesNotExist("missing"), "<b>fallback</b>"]

        notify_user_profile_rejected(user, UserRejectReason.intro)

        self.assertEqual(mock_render.call_count, 2)
        self.assertEqual(mock_render.call_args_list[1].args[0], "rejected/intro.html")


class TestNotifyUserPing(TestCase):
    @patch("notifications.telegram.users.send_telegram_message")
    def test_sends_ping_to_user(self, mock_send):
        user = _create_user("pinged_user")

        notify_user_ping(user, "Please update your intro")

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        self.assertEqual(call_kwargs["chat"].id, user.telegram_id)
        self.assertIn("Please update your intro", call_kwargs["text"])

    @patch("notifications.telegram.users.send_telegram_message")
    def test_skips_user_without_telegram(self, mock_send):
        user = _create_user("no_tg_ping", telegram_id=None)

        notify_user_ping(user, "message")

        mock_send.assert_not_called()


class TestNotifyAdminUserPing(TestCase):
    @patch("notifications.telegram.users.send_telegram_message")
    def test_sends_to_admin_chat(self, mock_send):
        user = _create_user("admin_pinged")

        notify_admin_user_ping(user, "test message")

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        self.assertIn(user.slug, call_kwargs["text"])


class TestNotifyUserAuth(TestCase):
    @patch("notifications.telegram.users.send_telegram_message")
    def test_sends_auth_code(self, mock_send):
        user = _create_user("auth_user")
        code = MagicMock()
        code.code = "123456"

        notify_user_auth(user, code)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        self.assertIn("123456", call_kwargs["text"])

    @patch("notifications.telegram.users.send_telegram_message")
    def test_skips_user_without_telegram(self, mock_send):
        user = _create_user("no_tg_auth", telegram_id=None)
        code = MagicMock()
        code.code = "123456"

        notify_user_auth(user, code)

        mock_send.assert_not_called()
