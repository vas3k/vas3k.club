import re
from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse

from comments.models import Comment
from posts.models.post import Post
from search.models import SearchIndex

from debug.helpers import HelperClient
from users.models.user import User


class SearchViewsTests(TestCase):
    new_user: User
    ids_count = 0

    @classmethod
    def setUpTestData(cls):
        cls.new_user: User = cls.create_user()
        cls.create_post(
            title="Дом дурачок 2023",
            text="Текст о доме дурачке год 2023. Купил ардуино и радуюсь",
        )
        cls.create_post(
            title="Где лучше купить домен?",
            text="Домен лучше купить потом",
        )
        cls.create_post(
            title="Очень оригинальный пост",
            text="В котором нет почти ничего из прошлых",
        )

    @classmethod
    def create_post(cls, **kwargs):
        cls.ids_count += 1
        post = Post.objects.create(
            type=kwargs.pop("type", Post.TYPE_POST),
            slug=kwargs.pop("slug", "test_{}".format(cls.ids_count)),
            title=kwargs.pop("title", "title_{}".format(cls.ids_count)),
            author=kwargs.pop("author", None) or cls.create_user(),
            moderation_status=Post.MODERATION_APPROVED,
            visibility=Post.VISIBILITY_EVERYWHERE,
            **kwargs,
        )
        SearchIndex.update_post_index(post)
        return post

    @classmethod
    def create_user(cls, **kwargs):
        user = User.objects.create(
            email=kwargs.pop("email", "testemail{}@xx.com".format(cls.ids_count)),
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            slug=kwargs.pop("slug", "slug{}".format(cls.ids_count)),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            **kwargs,
        )
        SearchIndex.update_user_index(user)
        return user

    def search(self, q="", content_type=None, ordering="-rank"):
        data = {"q": q, "ordering": ordering}
        if content_type:
            data["type"] = content_type
        return self.client.get(reverse("search"), data=data)

    def assert_search_results(self, q, expected_re, ordering="-rank", content_type=None, not_expected_re=None):
        response = self.search(q, content_type=content_type, ordering=ordering)
        text = response.content.decode()
        self.assertRegex(text, re.compile(expected_re, re.DOTALL | re.MULTILINE))
        if not_expected_re:
            self.assertNotRegex(text, re.compile(not_expected_re, re.DOTALL | re.MULTILINE))

    def setUp(self):
        self.client = HelperClient(user=self.new_user)
        self.client.authorise()

    def test_exact_results_must_be_first(self):
        self.assert_search_results("домен", "купить домен.*?Дом дурачок")
        self.assert_search_results("дом", "Дом дурачок.*?купить домен")
        self.assert_search_results("ардуино", "Дом дурачок", not_expected_re="домен|оригинальный")

    def test_stemming_works_too(self):
        self.assert_search_results("купить", "купить домен.*?Дом дурачок")
        self.assert_search_results("оригинально", "Очень оригинальный пост", not_expected_re="дурачок|домен")
        self.assert_search_results("прошлое", "Очень оригинальный пост", not_expected_re="дурачок|домен")

    def test_advanced_syntax(self):
        self.assert_search_results("купить дом", "купить домен.*?Дом дурачок", not_expected_re="оригинальный")
        self.assert_search_results('"купить дом"', "купить домен", not_expected_re="Дом дурачок")
        self.assert_search_results('"оригинальный домен"', "ничего не найдено")
        self.assert_search_results("оригинальный домен", "ничего не найдено")
        self.assert_search_results("оригинальный OR домен", "купить домен.*?оригинальный пост")

    def test_invalid_type_and_ordering_fallback_to_defaults(self):
        response = self.search("домен", content_type="invalid_type", ordering="invalid_ordering")

        self.assertEqual(response.context["type"], None)
        self.assertEqual(response.context["ordering"], "-rank")

    def test_type_post_excludes_intro_posts(self):
        intro = self.create_post(
            slug="intro_hidden",
            type=Post.TYPE_INTRO,
            title="INTRONLY TOKEN",
            text="INTRONLY TOKEN",
            author=self.new_user,
        )
        regular = self.create_post(
            slug="regular_visible",
            title="INTRONLY TOKEN regular",
            text="INTRONLY TOKEN regular",
            author=self.new_user,
        )
        SearchIndex.update_post_index(intro)
        SearchIndex.update_post_index(regular)

        response = self.search("INTRONLY TOKEN", content_type="post")
        content = response.content.decode()

        self.assertIn("regular_visible", content)
        self.assertNotIn("intro_hidden", content)

    def test_deleted_comments_are_excluded(self):
        post = self.create_post(
            slug="comment_post",
            title="Comment carrier",
            text="Comment carrier text",
            author=self.new_user,
        )
        comment = Comment.objects.create(
            post=post,
            author=self.new_user,
            text="UNIQUETOKEN_DELETED_COMMENT",
        )
        SearchIndex.update_comment_index(comment)
        comment.is_deleted = True
        comment.save(update_fields=["is_deleted"])

        response = self.search("UNIQUETOKEN_DELETED_COMMENT", content_type="comment")
        results = list(response.context["results"])

        self.assertEqual(results, [])

    def test_search_requires_auth(self):
        anonymous_client = HelperClient()

        response = anonymous_client.get(reverse("search"), data={"q": "домен"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/access_denied.html")
