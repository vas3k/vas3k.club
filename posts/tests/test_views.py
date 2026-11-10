import itertools
from datetime import datetime, timedelta

from django.urls import reverse
from django.test import TestCase

from debug.helpers import HelperClient
from users.models.user import User
from posts.models.post import Post
from posts.forms.compose import PostTextForm

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
            visibility=Post.VISIBILITY_EVERYWHERE,
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

class TestPostViews(TestCase):
    def setUp(self):
        self.creator = ModelCreator()
        self.user = self.creator.create_user()

    def test_show_post(self):
        post = self.creator.create_post(
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
                is_public=post_is_public,
            )
            post.visibility = Post.VISIBILITY_DRAFT
            post.save()

            client = self._authorized_client(user)

            response = client.get(self._post_url(post))

            self.assertContains(response=response, text='', status_code=404)
            # Post title should not be shown
            assert (
                post.title not in str(response.content)
            )

    def test_moderator_edit_keeps_actual_author_out_of_initial_coauthors(self):
        post = self.creator.create_post(coauthors=[])
        post.coauthors = [post.author.slug]
        post.save(update_fields=["coauthors"])
        self.user.roles = [User.ROLE_MODERATOR]
        self.user.save(update_fields=["roles"])
        client = self._authorized_client(self.user)
        response = client.get(reverse("edit_post", args=[post.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].instance.author_id, post.author_id)
        self.assertFalse(response.context["form"]["coauthors"].value())

    def test_compose_form_removes_author_but_keeps_other_coauthors(self):
        post = self.creator.create_post()
        form = PostTextForm(data={
            "title": "Edited title",
            "text": "Edited text",
            "coauthors": f"@{post.author.slug},{self.user.slug}",
            "is_public": "False",
        }, instance=post)

        self.assertTrue(form.is_valid(), form.errors)
        saved_post = form.save()
        saved_post.refresh_from_db()
        self.assertEqual(saved_post.author_id, post.author_id)
        self.assertEqual(saved_post.coauthors, [self.user.slug])

    @staticmethod
    def _post_url(post) -> str:
        return reverse('show_post', args=(post.type, post.slug))

    @staticmethod
    def _authorized_client(user):
        client = HelperClient(user)
        if user is not None:
            client.authorise()
        return client
