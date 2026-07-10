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
        self.assert_search_results('"купить дом"', "ничего не найдено")
        self.assert_search_results('"оригинальный домен"', "ничего не найдено")
        self.assert_search_results("оригинальный домен", "ничего не найдено")
        self.assert_search_results("оригинальный OR домен", "купить домен.*?оригинальный пост")

    def test_quoted_phrase_does_not_fallback_to_stemmed_match(self):
        self.create_post(
            slug="stemmed_phrase_variant",
            title="Я купил домены вчера",
            text="Я купил домены вчера",
            author=self.new_user,
        )

        response = self.search('"купить домен"')
        content = response.content.decode()

        self.assertIn("test_2", content)
        self.assertNotIn("stemmed_phrase_variant", content)

    def test_symbol_operators_and_parentheses(self):
        self.assert_search_results("(купить || дурачок) & дом", "Дом дурачок.*?купить домен")

    def test_minus_operator(self):
        self.create_post(
            slug="minus_keep",
            title="MINUS TOKEN KEEP",
            text="MINUS TOKEN KEEP",
            author=self.new_user,
        )
        self.create_post(
            slug="minus_drop",
            title="MINUS TOKEN DROP",
            text="MINUS TOKEN DROP",
            author=self.new_user,
        )
        self.assert_search_results("MINUS TOKEN -DROP", "minus_keep", not_expected_re="minus_drop")

    def test_minus_quoted_phrase_operator(self):
        self.create_post(
            slug="minus_phrase_keep",
            title="MINUS PHRASE TOKEN",
            text="MINUS PHRASE TOKEN and calm lake",
            author=self.new_user,
        )
        self.create_post(
            slug="minus_phrase_drop",
            title="MINUS PHRASE TOKEN",
            text="MINUS PHRASE TOKEN and broken bridge",
            author=self.new_user,
        )
        self.assert_search_results(
            'MINUS PHRASE TOKEN -"broken bridge"',
            "minus_phrase_keep",
            not_expected_re="minus_phrase_drop",
        )

    def test_custom_author_operator(self):
        vas3k = self.create_user(slug="vas3k", email="vas3k_test@example.com")
        self.create_post(
            slug="vas3k_post",
            title="AUTHOR FILTER TOKEN",
            text="AUTHOR FILTER TOKEN",
            author=vas3k,
        )
        self.create_post(
            slug="other_post",
            title="AUTHOR FILTER TOKEN",
            text="AUTHOR FILTER TOKEN",
            author=self.new_user,
        )

        response = self.search("AUTHOR FILTER TOKEN author:vas3k")
        slugs = [result.post.slug for result in response.context["results"] if result.post_id]

        self.assertIn("vas3k_post", slugs)
        self.assertNotIn("other_post", slugs)

    def test_custom_author_operator_is_case_insensitive(self):
        mixed_case_author = self.create_user(
            slug="MrSparkline",
            email="mrsparkline_test@example.com",
        )
        self.create_post(
            slug="mixed_case_author_post",
            title="AUTHOR CASE TOKEN",
            text="AUTHOR CASE TOKEN",
            author=mixed_case_author,
        )

        response = self.search("AUTHOR CASE TOKEN author:mrsparkline")
        slugs = [result.post.slug for result in response.context["results"] if result.post_id]

        self.assertIn("mixed_case_author_post", slugs)

    def test_custom_negative_author_operator(self):
        vas3k = self.create_user(slug="vas3kminus", email="vas3kminus_test@example.com")
        self.create_post(
            slug="author_minus_drop",
            title="AUTHOR MINUS TOKEN",
            text="AUTHOR MINUS TOKEN",
            author=vas3k,
        )
        self.create_post(
            slug="author_minus_keep",
            title="AUTHOR MINUS TOKEN",
            text="AUTHOR MINUS TOKEN",
            author=self.new_user,
        )

        response = self.search("AUTHOR MINUS TOKEN -author:vas3kminus")
        slugs = [result.post.slug for result in response.context["results"] if result.post_id]

        self.assertNotIn("author_minus_drop", slugs)
        self.assertIn("author_minus_keep", slugs)

    def test_custom_type_operator(self):
        post = self.create_post(
            slug="type_filter_post",
            title="TYPE FILTER TOKEN",
            text="TYPE FILTER TOKEN",
            author=self.new_user,
        )
        comment = Comment.objects.create(
            post=post,
            author=self.new_user,
            text="TYPE FILTER TOKEN",
        )
        SearchIndex.update_comment_index(comment)

        response = self.search("TYPE FILTER TOKEN type:comment")
        results = list(response.context["results"])

        self.assertTrue(results)
        self.assertTrue(all(result.type == SearchIndex.TYPE_COMMENT for result in results))

    def test_custom_negative_type_operator(self):
        post = self.create_post(
            slug="type_minus_post",
            title="TYPE MINUS TOKEN",
            text="TYPE MINUS TOKEN",
            author=self.new_user,
        )
        comment = Comment.objects.create(
            post=post,
            author=self.new_user,
            text="TYPE MINUS TOKEN",
        )
        SearchIndex.update_comment_index(comment)

        response = self.search("TYPE MINUS TOKEN -type:comment")
        results = list(response.context["results"])

        self.assertTrue(results)
        self.assertTrue(all(result.type != SearchIndex.TYPE_COMMENT for result in results))

    def test_custom_title_operator_for_posts(self):
        self.create_post(
            slug="title_keep_post",
            title="Space Elevator Handbook",
            text="TITLE POST TOKEN",
            author=self.new_user,
        )
        self.create_post(
            slug="title_drop_post",
            title="Ocean Farming Notes",
            text="TITLE POST TOKEN",
            author=self.new_user,
        )

        response = self.search("TITLE POST TOKEN title:elevator type:post")
        slugs = [result.post.slug for result in response.context["results"] if result.post_id]

        self.assertIn("title_keep_post", slugs)
        self.assertNotIn("title_drop_post", slugs)

    def test_custom_title_operator_with_quoted_value(self):
        self.create_post(
            slug="quoted_title_keep_post",
            title="Two Words Handbook",
            text="QUOTED TITLE TOKEN",
            author=self.new_user,
        )
        self.create_post(
            slug="quoted_title_drop_post",
            title="Two Ideas Handbook",
            text="QUOTED TITLE TOKEN",
            author=self.new_user,
        )

        response = self.search('QUOTED TITLE TOKEN title:"two words" type:post')
        slugs = [result.post.slug for result in response.context["results"] if result.post_id]

        self.assertIn("quoted_title_keep_post", slugs)
        self.assertNotIn("quoted_title_drop_post", slugs)

    def test_custom_title_operator_for_comments_uses_post_title(self):
        post_keep = self.create_post(
            slug="title_comment_post_keep",
            title="Distributed Tracing Deep Dive",
            text="Some post",
            author=self.new_user,
        )
        post_drop = self.create_post(
            slug="title_comment_post_drop",
            title="Kubernetes Operators Basics",
            text="Some post",
            author=self.new_user,
        )
        comment_keep = Comment.objects.create(
            post=post_keep,
            author=self.new_user,
            text="TITLE COMMENT TOKEN",
        )
        comment_drop = Comment.objects.create(
            post=post_drop,
            author=self.new_user,
            text="TITLE COMMENT TOKEN",
        )
        SearchIndex.update_comment_index(comment_keep)
        SearchIndex.update_comment_index(comment_drop)

        response = self.search("TITLE COMMENT TOKEN type:comment title:tracing")
        comment_ids = [result.comment_id for result in response.context["results"] if result.comment_id]

        self.assertIn(comment_keep.id, comment_ids)
        self.assertNotIn(comment_drop.id, comment_ids)

    def test_custom_title_operator_for_users_uses_full_name(self):
        keep_user = self.create_user(
            slug="title_user_keep",
            email="title_user_keep@example.com",
            full_name="Helena Quantum",
        )
        drop_user = self.create_user(
            slug="title_user_drop",
            email="title_user_drop@example.com",
            full_name="Martin Classical",
        )
        SearchIndex.update_user_index(keep_user)
        SearchIndex.update_user_index(drop_user)

        response = self.search("type:user title:quantum")
        user_slugs = [result.user.slug for result in response.context["results"] if result.user_id]

        self.assertIn("title_user_keep", user_slugs)
        self.assertNotIn("title_user_drop", user_slugs)

    def test_custom_negative_title_operator(self):
        self.create_post(
            slug="neg_title_keep_post",
            title="Rust Borrow Checker Guide",
            text="NEG TITLE TOKEN",
            author=self.new_user,
        )
        self.create_post(
            slug="neg_title_drop_post",
            title="Rust Async Runtime Guide",
            text="NEG TITLE TOKEN",
            author=self.new_user,
        )

        response = self.search("NEG TITLE TOKEN -title:async type:post")
        slugs = [result.post.slug for result in response.context["results"] if result.post_id]

        self.assertIn("neg_title_keep_post", slugs)
        self.assertNotIn("neg_title_drop_post", slugs)

    def test_since_until_year_month_day_filters(self):
        p_year = self.create_post(
            slug="since_year_post",
            title="DATE FILTER TOKEN",
            text="DATE FILTER TOKEN",
            author=self.new_user,
        )
        p_month = self.create_post(
            slug="since_month_post",
            title="DATE FILTER TOKEN",
            text="DATE FILTER TOKEN",
            author=self.new_user,
        )
        p_day = self.create_post(
            slug="since_day_post",
            title="DATE FILTER TOKEN",
            text="DATE FILTER TOKEN",
            author=self.new_user,
        )

        SearchIndex.objects.filter(post=p_year).update(created_at=datetime(2025, 1, 5))
        SearchIndex.objects.filter(post=p_month).update(created_at=datetime(2024, 1, 20))
        SearchIndex.objects.filter(post=p_day).update(created_at=datetime(2023, 4, 10, 8, 0, 0))

        year_response = self.search("DATE FILTER TOKEN since:2025 type:post")
        year_slugs = [result.post.slug for result in year_response.context["results"] if result.post_id]
        self.assertIn("since_year_post", year_slugs)
        self.assertNotIn("since_month_post", year_slugs)
        self.assertNotIn("since_day_post", year_slugs)

        month_response = self.search("DATE FILTER TOKEN until:2024-01 type:post")
        month_slugs = [result.post.slug for result in month_response.context["results"] if result.post_id]
        self.assertIn("since_month_post", month_slugs)
        self.assertIn("since_day_post", month_slugs)
        self.assertNotIn("since_year_post", month_slugs)

        day_response = self.search("DATE FILTER TOKEN since:2023-04-10 until:2023-04-10 type:post")
        day_slugs = [result.post.slug for result in day_response.context["results"] if result.post_id]
        self.assertIn("since_day_post", day_slugs)
        self.assertNotIn("since_month_post", day_slugs)
        self.assertNotIn("since_year_post", day_slugs)

    def test_invalid_since_until_filters_are_ignored(self):
        self.create_post(
            slug="invalid_date_filter_post",
            title="BAD DATE TOKEN",
            text="BAD DATE TOKEN",
            author=self.new_user,
        )

        response = self.search("BAD DATE TOKEN since:2024-99 until:aaaa type:post")
        slugs = [result.post.slug for result in response.context["results"] if result.post_id]

        self.assertIn("invalid_date_filter_post", slugs)

    def test_invalid_type_and_ordering_fallback_to_defaults(self):
        response = self.search("домен", content_type="invalid_type", ordering="invalid_ordering")

        self.assertEqual(response.context["type"], None)
        self.assertEqual(response.context["ordering"], "-rank")

    def test_popularity_ordering_is_allowed(self):
        response = self.search("домен", ordering="-upvotes")

        self.assertEqual(response.context["ordering"], "-upvotes")

    def test_ordering_form_keeps_selected_type(self):
        response = self.search("домен", content_type="post", ordering="-upvotes")
        content = response.content.decode()

        self.assertIn('<input type="hidden" name="type" value="post">', content)

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
