from django.test import Client, TestCase

from comments.models import Comment
from posts.models.post import Post
from search.api import MIN_PREFIX_LENGTH, MAX_PREFIX_LENGTH
from search.models import SearchIndex
from tags.models import Tag
from debug.utils_for_tests import create_approved_user, login


class TestSearchApiUsers(TestCase):
    def setUp(self):
        self.viewer = create_approved_user("search_api_viewer")
        self.client = Client()
        login(self.client, self.viewer)

    def test_users_prefix_too_short_returns_empty(self):
        create_approved_user("search_target")

        response = self.client.get("/search/users.json", data={"prefix": "ab"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["users"], [])

    def test_users_prefix_boundary_returns_matches(self):
        matched = create_approved_user("alpha_match")
        create_approved_user("beta_other")

        response = self.client.get("/search/users.json", data={"prefix": matched.slug[:MIN_PREFIX_LENGTH]})

        self.assertEqual(response.status_code, 200)
        slugs = [user["slug"] for user in response.json()["users"]]
        self.assertIn(matched.slug, slugs)

    def test_users_prefix_too_long_returns_empty(self):
        create_approved_user("longprefix_target")

        response = self.client.get("/search/users.json", data={"prefix": "a" * MAX_PREFIX_LENGTH})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["users"], [])

    def test_users_endpoint_rejects_post(self):
        response = self.client.post("/search/users.json", data={"prefix": "abc"})
        self.assertEqual(response.status_code, 405)


class TestSearchApiTags(TestCase):
    def setUp(self):
        self.viewer = create_approved_user("search_tag_viewer")
        self.client = Client()
        login(self.client, self.viewer)

    def test_tags_filter_by_group_and_prefix(self):
        Tag.objects.create(code="tech_py", name="Python", group=Tag.GROUP_TECH, is_visible=True)
        Tag.objects.create(code="club_py", name="PyClub", group=Tag.GROUP_CLUB, is_visible=True)
        Tag.objects.create(code="hidden_py", name="PyHidden", group=Tag.GROUP_TECH, is_visible=False)

        response = self.client.get("/search/tags.json", data={"group": Tag.GROUP_TECH, "prefix": "Pyt"})

        self.assertEqual(response.status_code, 200)
        codes = [tag["code"] for tag in response.json()["tags"]]
        self.assertEqual(codes, ["tech_py"])

    def test_tags_short_prefix_returns_empty(self):
        Tag.objects.create(code="short_pref", name="Python", group=Tag.GROUP_TECH, is_visible=True)

        response = self.client.get("/search/tags.json", data={"prefix": "py"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tags"], [])


class TestSearchJson(TestCase):
    def setUp(self):
        self.viewer = create_approved_user("search_json_viewer")
        self.author = create_approved_user("zxqsearchtoken", full_name="ZXQSEARCHTOKEN person")
        self.client = Client()
        login(self.client, self.viewer)

        self.post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="search_json_post",
            title="ZXQSEARCHTOKEN post title",
            text="Текст поста для search json",
            author=self.author,
            moderation_status=Post.MODERATION_APPROVED,
            visibility=Post.VISIBILITY_EVERYWHERE,
            is_public=True,
        )
        SearchIndex.update_post_index(self.post)

        self.intro = Post.objects.create(
            type=Post.TYPE_INTRO,
            slug="search_json_intro",
            title="ZXQSEARCHTOKEN intro",
            text="Интро не должно попадать в поиск по постам",
            author=self.author,
            moderation_status=Post.MODERATION_APPROVED,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )
        SearchIndex.update_post_index(self.intro)

        self.comment = Comment.objects.create(
            post=self.post,
            author=self.author,
            text="ZXQSEARCHTOKEN comment text",
        )
        SearchIndex.update_comment_index(self.comment)

        self.deleted_comment = Comment.objects.create(
            post=self.post,
            author=self.author,
            text="ZXQSEARCHTOKEN deleted comment",
            is_deleted=True,
        )
        SearchIndex.update_comment_index(self.deleted_comment)
        SearchIndex.update_user_index(self.author)

    def test_search_json_requires_auth(self):
        response = Client().get("/search.json", data={"q": "ZXQSEARCHTOKEN"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "api-auth-required")

    def test_search_json_rejects_empty_query(self):
        response = self.client.get("/search.json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["title"], "Пустой запрос")

    def test_search_json_returns_posts_comments_and_users(self):
        response = self.client.get("/search.json", data={"q": "ZXQSEARCHTOKEN"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["query"], "ZXQSEARCHTOKEN")
        self.assertIsNone(payload["type"])
        self.assertEqual(payload["ordering"], "-rank")
        self.assertEqual(payload["page"], 1)

        by_type = {}
        for item in payload["results"]:
            by_type.setdefault(item["type"], []).append(item)

        post_slugs = [item["post"]["_club"]["slug"] for item in by_type["post"]]
        self.assertIn(self.post.slug, post_slugs)
        self.assertIn(self.intro.slug, post_slugs)
        comment_texts = [item["comment"]["text"] for item in by_type["comment"]]
        self.assertEqual(comment_texts, [self.comment.text])
        self.assertEqual([item["user"]["slug"] for item in by_type["user"]], [self.author.slug])

    def test_search_json_post_type_skips_intros(self):
        response = self.client.get("/search.json", data={"q": "ZXQSEARCHTOKEN", "type": "post"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["type"], "post")
        slugs = [item["post"]["_club"]["slug"] for item in payload["results"]]
        self.assertEqual(slugs, [self.post.slug])

    def test_posts_resource_cannot_be_overridden_to_search_users(self):
        response = self.client.get("/search/posts.json", {"q": "ZXQSEARCHTOKEN", "type": "user"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["type"], "post")
        self.assertEqual([item["post"]["_club"]["slug"] for item in payload["results"]], [self.post.slug])

    def test_posts_search_excludes_stale_drafts_and_deleted_posts(self):
        self.post.visibility = Post.VISIBILITY_DRAFT
        self.post.save()

        response = self.client.get("/search/posts.json", {"q": "ZXQSEARCHTOKEN"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_posts_search_requires_authentication(self):
        response = Client().get("/search/posts.json", {"q": "ZXQSEARCHTOKEN"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "api-auth-required")
