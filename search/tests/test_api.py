from django.test import Client, TestCase

from search.api import MIN_PREFIX_LENGTH, MAX_PREFIX_LENGTH
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
        self.assertEqual(response.status_code, 400)


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
