import itertools
from datetime import datetime, timedelta

from django.urls import reverse
from django.test import TestCase

from debug.helpers import HelperClient
from users.models.user import User
from posts.models.post import Post

class ModelCreator:
    _exist_posts = 0
    _exist_users = 0

    def create_post(self, **kwargs):
        self._exist_posts += 1
        return Post.objects.create(
            type=Post.TYPE_POST,
            slug='test_{}'.format(self._exist_posts),
            title='title_{}'.format(self._exist_posts),
            author=self.create_user(),
            **kwargs,
        )

    def create_user(self):
        self._exist_users += 1
        return User.objects.create(
            email="testemail_{}@xx.com".format(self._exist_users),
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            slug="ujlbu4_{}".format(self._exist_users),
        )

class TestPaymentModel(TestCase):
    def setUp(self):
        self.creator = ModelCreator()
        self.user = self.creator.create_user()

    def test_show_post(self):
        post = self.creator.create_post(
            is_visible=True,
            is_public=True,
        )
        for user in [None, self.user]:
            client = self._authorized_client(user)

            response = client.get(self._post_url(post))

            self.assertContains(response=response, text='', status_code=200)

    def test_show_draft_post(self):
        '''
        Is regression test for #545.

        https://github.com/vas3k/vas3k.club/issues/545
        '''
        scenarios = itertools.product([None, self.user], [True, False])
        for user, post_is_public in scenarios:
            post = self.creator.create_post(
                is_visible=False,
                is_public=post_is_public,
            )
            client = self._authorized_client(user)

            response = client.get(self._post_url(post))

            self.assertContains(response=response, text='', status_code=404)
            # Post title should not be shown
            assert (
                post.title not in str(response.content)
            )

    @staticmethod
    def _post_url(post) -> str:
        return reverse('show_post', args=(post.type, post.slug))

    @staticmethod
    def _authorized_client(user):
        client = HelperClient(user)
        if user is not None:
            client.authorise()
        return client
