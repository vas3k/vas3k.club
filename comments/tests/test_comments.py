from django.test import TestCase
from django.test.client import RequestFactory
from comments.views import create_comment
from posts.models.subscriptions import PostSubscription

from posts.tests.test_views import ModelCreator


class PostSubscriptionCreator(ModelCreator):
    def create_subscription(self, user, post):
        return PostSubscription.objects.create(user=user, post=post, type="all")


class TestComments(TestCase):
    def setUp(self):
        self.creator = ModelCreator()
        subscr_creator = PostSubscriptionCreator()
        self.post = self.creator.create_post(
            is_visible=True,
            is_public=True,
        )
        self.author_user = self.post.author
        self.user_subscription = subscr_creator.create_subscription(
            self.author_user, self.post
        )

        rf = RequestFactory()
        self.comment_request = rf.post(
            (f"post/{self.post.id}/comment/create/", self.post.id),
            data={"text": "lorem ipsum", "subscribe_to_post": True},
        )

    def test_is_author_subscription_not_downgraded(self):
        self.comment_request.me = self.author_user

        self.assertEqual(
            self.user_subscription.type, PostSubscription.TYPE_ALL_COMMENTS
        )
        create_comment(self.comment_request, self.post.slug)
        self.user_subscription = PostSubscription.objects.get(
            user=self.author_user, post=self.post
        )
        self.assertEqual(
            self.user_subscription.type, PostSubscription.TYPE_ALL_COMMENTS
        )

    def test_is_usual_subscription_working(self):
        not_author_user = self.creator.create_user()
        self.comment_request.me = not_author_user
        self.assertRaises(
            PostSubscription.DoesNotExist,
            PostSubscription.objects.get,
            user=not_author_user,
            post=self.post,
        )
        create_comment(self.comment_request, self.post.slug)
        not_author_subscription = PostSubscription.objects.get(
            user=not_author_user, post=self.post
        )
        self.assertEqual(
            not_author_subscription.type, PostSubscription.TYPE_TOP_LEVEL_ONLY
        )
