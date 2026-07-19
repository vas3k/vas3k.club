from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.test import TestCase

from rooms.models import Room
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


class TestRoomModel(TestCase):
    def test_admins_with_details_preserves_order_and_skips_missing(self):
        admin_a = _create_user("room_admin_a")
        admin_b = _create_user("room_admin_b")
        room = Room.objects.create(
            slug="room-admins",
            title="Room Admins",
            color="#111111",
            admins=[admin_b.slug, "missing_slug", admin_a.slug],
        )

        result = room.admins_with_details

        self.assertEqual([u.slug for u in result], [admin_b.slug, admin_a.slug])

    def test_get_private_url_returns_none_without_links(self):
        room = Room.objects.create(
            slug="room-no-links",
            title="No Links",
            color="#111111",
        )

        self.assertIsNone(room.get_private_url())

    def test_to_dict_uses_private_redirect_url(self):
        room = Room.objects.create(
            slug="room-private-url",
            title="Private URL",
            color="#111111",
            chat_url="https://t.me/private_chat",
            chat_name="Private Chat",
        )

        data = room.to_dict()

        self.assertEqual(data["chat_url"], f"{settings.APP_HOST}{room.get_private_url()}")
