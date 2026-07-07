from datetime import datetime, timedelta

from django.test import TestCase

from clickers.models import Click, MAX_CLICKER_ID_LEN
from users.models.user import User


def _create_user(slug):
    return User.objects.create(
        slug=slug,
        email=f"{slug}@test.com",
        full_name=slug,
        membership_started_at=datetime.utcnow() - timedelta(days=30),
        membership_expires_at=datetime.utcnow() + timedelta(days=30),
        moderation_status=User.MODERATION_STATUS_APPROVED,
        is_email_verified=True,
    )


class TestClickersModel(TestCase):
    def test_toggle_is_idempotent(self):
        user = _create_user("clicker_user")
        clicker_id = "my_clicker"

        created = Click.toggle(user, clicker_id)
        deleted = Click.toggle(user, clicker_id)

        self.assertTrue(created)
        self.assertFalse(deleted)
        self.assertEqual(Click.objects.count(), 0)

    def test_list_truncates_clicker_id_to_max_length(self):
        user = _create_user("clicker_long_user")
        long_id = "x" * (MAX_CLICKER_ID_LEN + 20)
        Click.toggle(user, long_id)

        clicks = list(Click.list(long_id))

        self.assertEqual(len(clicks), 1)
        self.assertEqual(clicks[0].clicker_id, "x" * MAX_CLICKER_ID_LEN)
