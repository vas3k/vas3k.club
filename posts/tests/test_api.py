from datetime import datetime

from django.test import Client, TestCase

from posts.tests.test_views import ModelCreator


class TestApi(TestCase):
    def setUp(self):
        self.creator = ModelCreator()
        self.user = self.creator.create_user()
        self.time = datetime.now()

    def test_date_rfc3339(self):
        post = self.creator.create_post(
            is_public=True,
        )
        post.published_at = self.time
        post.updated_at = self.time
        converted_post = post.to_dict()
        self.assertIsNotNone(
            datetime.strptime(
                converted_post["date_published"], "%Y-%m-%dT%H:%M:%S.%f%z"
            ).tzinfo,
        )
        self.assertIsNotNone(
            datetime.strptime(
                converted_post["date_modified"], "%Y-%m-%dT%H:%M:%S.%f%z"
            ).tzinfo,
        )

    def test_content_text_is_not_none(self):
        post = self.creator.create_post(
            is_public=False,
        )
        converted_post = post.to_dict()
        self.assertIsNotNone(converted_post["content_text"])

    def _client_for(self, user):
        from authn.models.session import Session
        client = Client()
        client.cookies["token"] = Session.create_for_user(user).token
        return client

    def _private_post(self):
        return self.creator.create_post(
            is_public=False,
            text="secret private text",
            moderation_status="approved",
            published_at=datetime.now(),
        )

    def test_json_masks_private_post_for_anonymous(self):
        post = self._private_post()
        response = Client().get(f"/post/{post.slug}.json")
        self.assertNotIn("secret private text", response.content.decode())

    def test_json_masks_private_post_for_banned_user(self):
        # security: banned users must not read private content via .json
        from datetime import timedelta
        post = self._private_post()
        banned = self.creator.create_user()
        banned.is_banned_until = datetime.now() + timedelta(days=30)
        banned.save()

        response = self._client_for(banned).get(f"/post/{post.slug}.json")
        self.assertNotIn("secret private text", response.content.decode())

    def test_json_masks_private_post_for_expired_user(self):
        # security: expired membership must not read private content via .json
        from datetime import timedelta
        post = self._private_post()
        expired = self.creator.create_user()
        expired.membership_expires_at = datetime.now() - timedelta(days=1)
        expired.save()

        response = self._client_for(expired).get(f"/post/{post.slug}.json")
        self.assertNotIn("secret private text", response.content.decode())

    def test_json_unmasks_private_post_for_active_member(self):
        post = self._private_post()
        member = self.creator.create_user()

        response = self._client_for(member).get(f"/post/{post.slug}.json")
        self.assertIn("secret private text", response.content.decode())
