from datetime import datetime, timedelta

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from authn.models.openid import OAuth2App, OAuth2Token
from debug.utils_for_tests import create_approved_user, login
from tags.models import Tag, UserTag
from users.models.friends import Friend
from users.models.user import User


class TestUserApi(TestCase):
    def setUp(self):
        self.owner = create_approved_user("api_owner", telegram_data={"username": "private_handle"})
        self.other = create_approved_user("api_other")
        self.app = OAuth2App.objects.create(name="API test app", owner=self.owner, scope="openid")
        self.profile_url = reverse("api_profile", args=["me"])
        self.friend_url = reverse("api_friend", args=[self.other.slug])

    def test_service_token_authenticates_as_app_owner(self):
        response = self.client.get(self.profile_url, headers={"X-Service-Token": self.app.service_token})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["id"], str(self.owner.id))
        self.assertNotIn("email", response.json()["user"])
        self.assertNotIn("telegram", response.json()["user"])

    def test_contact_scope_controls_private_fields(self):
        for scope in ["openid", "openid contact"]:
            with self.subTest(scope=scope):
                self.app.scope = scope
                self.app.save(update_fields=["scope"])

                response = self.client.get(self.profile_url, headers={"X-Service-Token": self.app.service_token})

                self.assertEqual(response.status_code, 200)
                user = response.json()["user"]
                self.assertEqual("email" in user, "contact" in scope)
                self.assertEqual("telegram" in user, "contact" in scope)

                if "contact" in scope:
                    self.assertEqual(user["email"], self.owner.email)
                    self.assertEqual(user["telegram"], self.owner.telegram_data)

    def test_bearer_identity_takes_precedence_over_cookie(self):
        login(self.client, self.other)
        token = OAuth2Token.objects.create(
            user=self.owner, client_id=self.app.client_id, token_type="Bearer",
            access_token="api-bearer", refresh_token="api-refresh", scope="openid",
            expires_in=3600,
        )

        response = self.client.get(self.profile_url, headers={"Authorization": f"Bearer {token.access_token}"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["id"], str(self.owner.id))

    def test_revoked_or_expired_bearer_cannot_fall_back_to_cookie(self):
        login(self.client, self.other)
        token = OAuth2Token.objects.create(
            user=self.owner, client_id=self.app.client_id, token_type="Bearer",
            access_token="api-rejected-bearer", refresh_token="api-refresh", scope="openid",
            expires_in=3600, revoked=True,
        )

        response = self.client.get(self.profile_url, headers={"Authorization": f"Bearer {token.access_token}"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "api-auth-required")
        OAuth2Token.objects.filter(id=token.id).update(
            revoked=False,
            issued_at=datetime.utcnow() - timedelta(seconds=settings.OPENID_JWT_EXPIRE_SECONDS + 1),
        )

        response = self.client.get(self.profile_url, headers={"Authorization": f"Bearer {token.access_token}"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "api-auth-required")

    def test_invalid_service_token_cannot_fall_back_to_cookie(self):
        login(self.client, self.other)

        response = self.client.post(self.friend_url, headers={"X-Service-Token": "invalid-service-token"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "api-auth-required")
        self.assertFalse(Friend.objects.exists())

    def test_membership_and_moderation_denials_do_not_mutate_state(self):
        states = [
            ({"is_banned_until": datetime.utcnow() + timedelta(days=1)}, "banned"),
            ({"membership_expires_at": datetime.utcnow() - timedelta(days=1)}, "membership_expired"),
            ({"moderation_status": User.MODERATION_STATUS_ON_REVIEW}, "on_review"),
        ]

        for updates, expected_code in states:
            with self.subTest(code=expected_code):
                User.objects.filter(id=self.owner.id).update(
                    is_banned_until=None,
                    membership_expires_at=datetime.utcnow() + timedelta(days=30),
                    moderation_status=User.MODERATION_STATUS_APPROVED,
                )
                User.objects.filter(id=self.owner.id).update(**updates)

                response = self.client.post(self.friend_url, headers={"X-Service-Token": self.app.service_token})

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], expected_code)
                self.assertFalse(Friend.objects.exists())

    def test_friend_toggle_changes_only_authenticated_users_relation(self):
        login(self.client, self.other)
        target_url = reverse("api_friend", args=[self.other.slug])
        self.assertEqual(target_url, f"/user/{self.other.slug}/friends.json")
        headers = {"X-Service-Token": self.app.service_token}

        response = self.client.post(target_url, headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "created")
        self.assertTrue(Friend.objects.filter(user_from=self.owner, user_to=self.other).exists())
        self.assertFalse(Friend.objects.filter(user_from=self.other).exists())

        response = self.client.delete(target_url, headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "deleted")
        self.assertFalse(Friend.objects.exists())

    def test_get_tag_toggle_does_not_create_membership(self):
        tag = Tag.objects.create(code="api_test_tag", name="API tag")
        login(self.client, self.owner)

        url = reverse("toggle_tag", args=[tag.code])
        self.assertEqual(url, f"/profile/tags/{tag.code}.json")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserTag.objects.exists())

    def test_self_friendship_is_rejected_without_mutation(self):
        login(self.client, self.owner)

        response = self.client.post(reverse("api_friend", args=[self.owner.slug]))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Friend.objects.exists())
