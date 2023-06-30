from django.test import TestCase
from django.test.client import RequestFactory
from comments.views import create_comment
from posts.models.subscriptions import PostSubscription

from posts.tests.test_views import ModelCreator

class TestComments(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.creator = ModelCreator()
        self.user = self.creator.create_user()
        self.post = self.creator.create_post(
            is_visible=True,
            is_public=True,
        )

    def test_is_subscription_not_downgraded(self):
        comment_form = {"text": "-", "subscribe_to_post": True}
        comment_request = self.rf.post((f"post/{self.post.id}/comment/create/", self.post.id),
                                       data=comment_form)
        comment_request.me = self.user
        create_comment(comment_request, self.post.id)
        subscription: PostSubscription = PostSubscription.objects.filter(user=self.user, post=self.post).qs
        self.assertTrue(subscription.type == PostSubscription.TYPE_ALL_COMMENTS)

