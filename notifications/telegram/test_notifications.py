from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import TestCase

from comments.models import Comment
from notifications.telegram.comments import notify_on_comment_created
from notifications.telegram.posts import notify_author_friends, notify_users_by_username
from posts.models.post import Post
from users.models.mute import UserMuted
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


class TestCommentMentionNotifications(TestCase):
    def setUp(self):
        self.author = _create_user("comment_author", telegram_id=None)
        self.mentioned = [_create_user(f"mentioned_{i}") for i in range(5)]
        self.post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="comment_mention_post",
            title="Test",
            text="body",
            author=self.author,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )
        self.parent_comment = Comment.objects.create(
            author=self.author,
            post=self.post,
            text="parent",
        )

    def _create_reply_with_mentions(self, text):
        return Comment.objects.create(
            author=self.author,
            post=self.post,
            reply_to=self.parent_comment,
            text=text,
        )

    @patch("notifications.telegram.comments.send_telegram_message")
    @patch("notifications.telegram.comments.render_html_message", return_value="<b>test</b>")
    @patch("notifications.telegram.comments.PostSubscription.post_subscribers", return_value=[])
    def test_notifies_all_mentioned_users(self, mock_subs, mock_render, mock_send):
        mentions = " ".join(f"@{u.slug}" for u in self.mentioned)
        comment = self._create_reply_with_mentions(f"Hey {mentions} check this out")

        # 1 who_muted_user + 1 in_bulk = 2 queries
        with self.assertNumQueries(2):
            notify_on_comment_created(comment)

        self.assertEqual(mock_send.call_count, 5)

    @patch("notifications.telegram.comments.send_telegram_message")
    @patch("notifications.telegram.comments.render_html_message", return_value="<b>test</b>")
    @patch("notifications.telegram.comments.PostSubscription.post_subscribers", return_value=[])
    def test_skips_nonexistent_mentioned_users(self, mock_subs, mock_render, mock_send):
        comment = self._create_reply_with_mentions("@nonexistent_user_abc hello")

        notify_on_comment_created(comment)

        mock_send.assert_not_called()

    @patch("notifications.telegram.comments.send_telegram_message")
    @patch("notifications.telegram.comments.render_html_message", return_value="<b>test</b>")
    @patch("notifications.telegram.comments.PostSubscription.post_subscribers", return_value=[])
    def test_does_not_notify_muted_users(self, mock_subs, mock_render, mock_send):
        target_user = self.mentioned[0]
        UserMuted.objects.create(user_from=target_user, user_to=self.author)

        comment = self._create_reply_with_mentions(f"@{target_user.slug} hello")

        notify_on_comment_created(comment)

        mock_send.assert_not_called()

    @patch("notifications.telegram.comments.notify_moderators_on_mention")
    @patch("notifications.telegram.comments.send_telegram_message")
    @patch("notifications.telegram.comments.render_html_message", return_value="<b>test</b>")
    @patch("notifications.telegram.comments.PostSubscription.post_subscribers", return_value=[])
    def test_moderator_mention_triggers_moderator_notification(self, mock_subs, mock_render, mock_send, mock_mod):
        comment = self._create_reply_with_mentions("@moderator please check")

        notify_on_comment_created(comment)

        mock_mod.assert_called_once_with(comment)
        mock_send.assert_not_called()

    @patch("notifications.telegram.comments.send_telegram_message")
    @patch("notifications.telegram.comments.render_html_message", return_value="<b>test</b>")
    @patch("notifications.telegram.comments.PostSubscription.post_subscribers", return_value=[])
    def test_duplicate_mention_sends_one_notification(self, mock_subs, mock_render, mock_send):
        target = self.mentioned[0]
        comment = self._create_reply_with_mentions(f"@{target.slug} and again @{target.slug}")

        notify_on_comment_created(comment)

        self.assertEqual(mock_send.call_count, 1)

    @patch("notifications.telegram.comments.send_telegram_message")
    @patch("notifications.telegram.comments.render_html_message", return_value="<b>test</b>")
    @patch("notifications.telegram.comments.PostSubscription.post_subscribers", return_value=[])
    @patch("notifications.telegram.comments.Friend.friends_for_user", return_value=[])
    def test_top_level_comment_mentions_with_channel(self, mock_friends, mock_subs, mock_render, mock_send):
        """Top-level comment sends to CLUB_ONLINE channel + notifies mentioned users."""
        target = self.mentioned[0]
        comment = Comment.objects.create(
            author=self.author,
            post=self.post,
            text=f"@{target.slug} look",
        )

        notify_on_comment_created(comment)

        # 1 channel message (CLUB_ONLINE) + 1 mention notification
        self.assertEqual(mock_send.call_count, 2)


class TestPostMentionNotifications(TestCase):
    def setUp(self):
        self.author = _create_user("post_author", telegram_id=None)
        self.mentioned = [_create_user(f"post_mentioned_{i}") for i in range(5)]

    def _create_post_with_mentions(self):
        mentions = " ".join(f"@{u.slug}" for u in self.mentioned)
        return Post.objects.create(
            type=Post.TYPE_POST,
            slug="post_mention",
            title="Test",
            text=f"Hey {mentions} check this",
            author=self.author,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )

    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>test</b>")
    @patch("notifications.telegram.posts.Friend.friends_for_user", return_value=[])
    def test_notify_author_friends_notifies_mentioned(self, mock_friends, mock_render, mock_send):
        post = self._create_post_with_mentions()

        with self.assertNumQueries(1):
            notify_author_friends(post)

        self.assertEqual(mock_send.call_count, 5)

    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>test</b>")
    @patch("notifications.telegram.posts.Friend.friends_for_user", return_value=[])
    def test_notify_author_friends_skips_no_telegram(self, mock_friends, mock_render, mock_send):
        no_tg_user = _create_user("no_telegram_user", telegram_id=None)
        post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="post_no_tg",
            title="Test",
            text=f"@{no_tg_user.slug} hey",
            author=self.author,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )

        notify_author_friends(post)

        mock_send.assert_not_called()

    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>test</b>")
    def test_notify_users_by_username_sends_to_all(self, mock_render, mock_send):
        post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="post_coauthor_test",
            title="Test",
            text="body",
            author=self.author,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )
        slugs = [u.slug for u in self.mentioned]

        with self.assertNumQueries(1):
            notify_users_by_username(slugs, "coauthor_added.html", post)

        self.assertEqual(mock_send.call_count, 5)

    @patch("notifications.telegram.posts.send_telegram_message")
    @patch("notifications.telegram.posts.render_html_message", return_value="<b>test</b>")
    def test_notify_users_by_username_ignores_nonexistent(self, mock_render, mock_send):
        post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="post_coauthor_missing",
            title="Test",
            text="body",
            author=self.author,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )

        notify_users_by_username(["nonexistent_slug_xyz"], "coauthor_added.html", post)

        mock_send.assert_not_called()
