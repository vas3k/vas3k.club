from datetime import datetime, timedelta, timezone

from django.test import TestCase

from common.data.colors import COOL_COLORS
from tags.models import Tag, UserTag
from users.models.user import User


def _create_user(slug):
    return User.objects.create(
        slug=slug,
        email=f"{slug}@test.com",
        full_name=slug,
        membership_started_at=datetime.now(timezone.utc) - timedelta(days=10),
        membership_expires_at=datetime.now(timezone.utc) + timedelta(days=10),
        moderation_status=User.MODERATION_STATUS_APPROVED,
        is_email_verified=True,
    )


class TestTagModel(TestCase):
    def test_color_is_deterministic_for_same_code(self):
        tag = Tag.objects.create(code="python", name="Python", group=Tag.GROUP_TECH)
        expected = COOL_COLORS[sum(map(ord, "python")) % len(COOL_COLORS)]

        self.assertEqual(tag.color, expected)

    def test_group_display_falls_back_for_unknown_group(self):
        tag = Tag.objects.create(code="mystery", name="Mystery", group="unexpected")

        self.assertEqual(tag.group_display(), Tag.GROUP_OTHER)

    def test_tags_with_stats_returns_only_visible_tags(self):
        user = _create_user("tag_user")
        visible_tag = Tag.objects.create(code="visible_tag", name="Visible", is_visible=True)
        Tag.objects.create(code="hidden_tag", name="Hidden", is_visible=False)
        UserTag.objects.create(user=user, tag=visible_tag, name=visible_tag.name)

        tags = list(Tag.tags_with_stats().order_by("code"))

        self.assertEqual([tag.code for tag in tags], ["visible_tag"])
        self.assertEqual(tags[0].user_count, 1)
