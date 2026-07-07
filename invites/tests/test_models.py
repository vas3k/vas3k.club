from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import TestCase

from invites.models import INVITE_CODE_LENGTH, INVITE_EXPIRATION_DAYS, Invite
from payments.models import Payment
from payments.products import PRODUCTS
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


def _create_payment(user, reference):
    return Payment.create(
        reference=reference,
        user=user,
        product=PRODUCTS["club1_invite"],
        status=Payment.STATUS_SUCCESS,
        data={"source": "tests"},
    )


class TestInviteModel(TestCase):
    @patch("invites.models.random_string", return_value="abc123abc123ab")
    def test_save_generates_uppercase_code(self, _mock_random):
        user = _create_user("invite_code_user")
        payment = _create_payment(user, "invite-code-ref")

        invite = Invite.objects.create(user=user, payment=payment, code="")

        self.assertEqual(len(invite.code), INVITE_CODE_LENGTH)
        self.assertEqual(invite.code, "ABC123ABC123AB")

    def test_is_expired_and_is_used_flags(self):
        user = _create_user("invite_flags_user")
        payment = _create_payment(user, "invite-flag-ref")
        invite = Invite.objects.create(user=user, payment=payment, code="FLAGSCODE12345")

        Invite.objects.filter(id=invite.id).update(
            created_at=datetime.utcnow() - timedelta(days=INVITE_EXPIRATION_DAYS + 1)
        )
        invite.refresh_from_db()

        self.assertTrue(invite.is_expired)
        self.assertFalse(invite.is_used)

        invite.used_at = datetime.utcnow()
        invite.save(update_fields=["used_at"])
        invite.refresh_from_db()
        self.assertTrue(invite.is_used)
