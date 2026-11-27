from django.test import TestCase
from django.urls import reverse

from debug.utils_for_tests import create_approved_user, login
from users.models.mute import UserMuted


class UnmutePermissionsTest(TestCase):
    def setUp(self):
        self.user = create_approved_user("mute-owner")
        self.target = create_approved_user("mute-target")
        login(self.client, self.user)

    def test_can_unmute_user_promoted_to_moderator(self):
        UserMuted.mute(self.user, self.target)
        self.target.roles = ["moderator"]
        self.target.save()
        url = reverse("toggle_mute", args=[self.target.slug])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertFalse(UserMuted.is_muted(self.user, self.target))

    def test_cannot_mute_moderator_or_self(self):
        self.target.roles = ["moderator"]
        self.target.save()

        for target in [self.target, self.user]:
            with self.subTest(target=target.slug):
                response = self.client.post(reverse("toggle_mute", args=[target.slug]))
                self.assertEqual(response.status_code, 400)
                self.assertFalse(UserMuted.is_muted(self.user, target))

    def test_cannot_access_another_users_mute_list(self):
        response = self.client.get(reverse("muted", args=[self.target.slug]))
        self.assertEqual(response.status_code, 403)
