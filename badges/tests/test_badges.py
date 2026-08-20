from datetime import datetime, timedelta

from django.test import TestCase

from badges.models import Badge, UserBadge
from club.exceptions import BadRequest, ContentDuplicated, InsufficientFunds
from comments.models import Comment
from posts.models.post import Post
from users.models.user import User


def _create_user(slug, membership_days=30):
    return User.objects.create(
        slug=slug,
        email=f"{slug}@test.com",
        full_name=slug,
        membership_started_at=datetime.utcnow() - timedelta(days=30),
        membership_expires_at=datetime.utcnow() + timedelta(days=membership_days),
        moderation_status=User.MODERATION_STATUS_APPROVED,
        is_email_verified=True,
    )


class TestUserBadgeBusinessLogic(TestCase):
    def setUp(self):
        self.badge = Badge.objects.create(
            code="test_badge",
            title="Test Badge",
            description="Test Description",
            price_days=5,
        )
        self.from_user = _create_user("badge_from", membership_days=120)
        self.to_user = _create_user("badge_to", membership_days=30)
        self.post = Post.objects.create(
            slug="badge-post",
            type=Post.TYPE_POST,
            title="Badge Post",
            text="Text",
            author=self.to_user,
            visibility=Post.VISIBILITY_EVERYWHERE,
            metadata={},
        )

    def test_cannot_gift_badge_to_yourself(self):
        with self.assertRaises(BadRequest):
            UserBadge.create_user_badge(
                badge=self.badge,
                from_user=self.from_user,
                to_user=self.from_user,
                post=self.post,
            )

    def test_cannot_gift_badge_with_insufficient_days(self):
        poor_user = _create_user("badge_poor", membership_days=2)

        with self.assertRaises(InsufficientFunds):
            UserBadge.create_user_badge(
                badge=self.badge,
                from_user=poor_user,
                to_user=self.to_user,
                post=self.post,
            )

    def test_create_user_badge_deducts_balance_and_updates_post_metadata(self):
        from_before = self.from_user.membership_expires_at

        user_badge = UserBadge.create_user_badge(
            badge=self.badge,
            from_user=self.from_user,
            to_user=self.to_user,
            post=self.post,
            note="Thanks!",
        )

        self.from_user.refresh_from_db()
        self.post.refresh_from_db()

        self.assertEqual(user_badge.badge_id, self.badge.code)
        self.assertAlmostEqual(
            self.from_user.membership_expires_at,
            from_before - timedelta(days=self.badge.price_days),
            delta=timedelta(seconds=2),
        )
        self.assertEqual(self.post.metadata["badges"][self.badge.code]["count"], 1)

    def test_duplicate_badge_for_same_post_is_rejected(self):
        UserBadge.create_user_badge(
            badge=self.badge,
            from_user=self.from_user,
            to_user=self.to_user,
            post=self.post,
        )

        with self.assertRaises(ContentDuplicated):
            UserBadge.create_user_badge(
                badge=self.badge,
                from_user=self.from_user,
                to_user=self.to_user,
                post=self.post,
            )

    def test_to_dict_handles_null_post_from_comment_badge(self):
        comment_author = _create_user("badge_comment_author")
        post = Post.objects.create(
            slug="badge-comment-post",
            type=Post.TYPE_POST,
            title="Badge Comment Post",
            text="Text",
            author=comment_author,
            visibility=Post.VISIBILITY_EVERYWHERE,
            metadata={},
        )
        comment = Comment.objects.create(post=post, author=comment_author, text="Nice")

        user_badge = UserBadge.create_user_badge(
            badge=self.badge,
            from_user=self.from_user,
            to_user=comment_author,
            comment=comment,
        )

        data = user_badge.to_dict()
        self.assertIsNone(data["post"])
        self.assertEqual(data["comment"], {"id": comment.id})

    def test_to_dict_handles_null_comment_from_post_badge(self):
        user_badge = UserBadge.create_user_badge(
            badge=self.badge,
            from_user=self.from_user,
            to_user=self.to_user,
            post=self.post,
        )

        data = user_badge.to_dict()
        self.assertIsNone(data["comment"])
        self.assertEqual(data["post"], {"id": self.post.id})
