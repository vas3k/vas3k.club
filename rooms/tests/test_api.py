from django.test import TestCase
from django.urls import reverse

from debug.utils_for_tests import create_approved_user, login
from rooms.models import Room, RoomMuted, RoomSubscription


class TestRoomApiResources(TestCase):
    def setUp(self):
        self.user = create_approved_user("room_api_user")
        self.room = Room.objects.create(slug="room-api-resource", title="Resource room")
        login(self.client, self.user)

    def test_subscription_methods_preserve_chat_membership(self):
        url = reverse("toggle_room_subscription", args=[self.room.slug])
        self.assertEqual(url, f"/room/{self.room.slug}/subscriptions.json")
        RoomSubscription.join_chat(self.user, self.room)

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_subscribed"])

        for method, expected in [(self.client.post, True), (self.client.delete, False)]:
            for attempt in range(2):
                response = method(url)
                membership = RoomSubscription.objects.get(user=self.user, room=self.room)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["is_subscribed"], expected)
                self.assertEqual(membership.is_notified, expected)
                self.assertTrue(membership.is_chat_member)
                self.assertEqual(RoomSubscription.objects.count(), 1)

    def test_room_mute_is_per_user_and_idempotent(self):
        url = reverse("toggle_room_mute", args=[self.room.slug])
        self.assertEqual(url, f"/room/{self.room.slug}/mutes.json")
        other = create_approved_user("room_api_other")
        RoomMuted.mute(other, self.room)

        response = self.client.get(url)

        self.assertFalse(response.json()["is_muted"])
        self.assertEqual(RoomMuted.objects.count(), 1)

        for method, expected in [(self.client.post, True), (self.client.delete, False)]:
            for attempt in range(2):
                response = method(url)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["is_muted"], expected)
                self.assertEqual(RoomMuted.objects.filter(user=self.user).exists(), expected)
                self.assertTrue(RoomMuted.objects.filter(user=other).exists())
