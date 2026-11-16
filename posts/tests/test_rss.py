from types import SimpleNamespace
from unittest import TestCase

from posts.rss import NewPostsRss


class TestRssPrivacy(TestCase):
    def test_public_body_is_bounded_and_escaped(self):
        post = SimpleNamespace(is_public=True, text="Public text " * 1000, description="Short teaser")
        description = str(NewPostsRss().item_description(post))
        self.assertEqual(len(description), 5000)
        self.assertNotEqual(description, post.description)

    def test_members_body_never_enters_rss(self):
        post = SimpleNamespace(is_public=False, text="PRIVATE BODY MUST STAY PRIVATE " * 100,
                               description="Existing public teaser")
        self.assertEqual(NewPostsRss().item_description(post), post.description)
