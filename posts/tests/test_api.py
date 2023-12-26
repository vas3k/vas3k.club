from datetime import datetime

from django.test import TestCase

from posts.tests.test_views import ModelCreator


class TestApi(TestCase):
    def setUp(self):
        self.creator = ModelCreator()
        self.user = self.creator.create_user()
        self.time = datetime.now()

    def test_date_rfc3339(self):
        post = self.creator.create_post(
            is_visible=True,
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
            is_visible=True,
            is_public=False,
        )
        converted_post = post.to_dict()
        self.assertIsNotNone(converted_post["content_text"])
