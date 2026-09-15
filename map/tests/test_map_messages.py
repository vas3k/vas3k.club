import json
from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import TestCase

from authn.models.session import Session
from map.models import MapMessages, MapMessageVote
from map.templatetags.map import map_messages_geo_json
from users.models.user import User

_SLUG_PREFIX = "tmapmsg_"


def _create_user(suffix, **kwargs):
    slug = f"{_SLUG_PREFIX}{suffix}"
    defaults = dict(
        email=f"{slug}@test.com",
        full_name=slug,
        membership_started_at=datetime.now() - timedelta(days=5),
        membership_expires_at=datetime.now() + timedelta(days=5),
        moderation_status=User.MODERATION_STATUS_APPROVED,
    )
    defaults.update(kwargs)
    return User.objects.create(slug=slug, **defaults)


def _login(client, user):
    session = Session.create_for_user(user)
    client.cookies["token"] = session.token


class TestCreateMapMessage(TestCase):
    def setUp(self):
        self.user = _create_user("author")
        _login(self.client, self.user)
        self.url = "/map/messages/create.json"

    def _post(self, **kwargs):
        data = dict(text="Привет с карты", latitude=52.52, longitude=13.4)
        data.update(kwargs)
        return self.client.post(self.url, data=data)

    def test_creates_message_and_returns_geojson_feature(self):
        response = self._post()

        self.assertEqual(response.status_code, 200)
        message = MapMessages.objects.get(author=self.user)
        self.assertEqual(message.text, "Привет с карты")
        self.assertAlmostEqual(message.latitude, 52.52)
        self.assertAlmostEqual(message.longitude, 13.4)

        feature = response.json()["feature"]
        self.assertEqual(feature["properties"]["id"], str(message.id))
        self.assertEqual(feature["properties"]["text"], "Привет с карты")
        self.assertEqual(feature["properties"]["author_url"], f"/user/{self.user.slug}/")
        self.assertEqual(feature["geometry"]["coordinates"], [13.4, 52.52])
        self.assertFalse(response.json()["can_post"])

    def test_strips_whitespace_and_rejects_empty_text(self):
        response = self._post(text="   \n  ")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(MapMessages.objects.exists())

    def test_rejects_text_longer_than_the_limit(self):
        response = self._post(text="x" * (MapMessages.MAX_TEXT_LENGTH + 1))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(MapMessages.objects.exists())

    def test_accepts_text_of_exactly_the_limit(self):
        response = self._post(text="x" * MapMessages.MAX_TEXT_LENGTH)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(MapMessages.objects.get().text), MapMessages.MAX_TEXT_LENGTH)

    def test_rejects_non_numeric_coordinates(self):
        response = self._post(latitude="somewhere")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(MapMessages.objects.exists())

    def test_rejects_coordinates_outside_the_map(self):
        response = self._post(latitude=91.0)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(MapMessages.objects.exists())

    def test_rejects_get_requests(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)
        self.assertFalse(MapMessages.objects.exists())

    def test_requires_auth(self):
        self.client.cookies.clear()

        response = self._post()

        self.assertEqual(response.status_code, 400)
        self.assertFalse(MapMessages.objects.exists())

    def test_allows_only_one_message_a_day(self):
        self._post()

        response = self._post(text="И ещё одно")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["title"], "Подождите 24 часа")
        self.assertEqual(MapMessages.objects.count(), 1)

    def test_allows_the_next_message_when_the_cooldown_is_over(self):
        self._post()
        MapMessages.objects.update(
            created_at=datetime.utcnow() - MapMessages.POST_COOLDOWN - timedelta(minutes=1)
        )

        response = self._post(text="Прошли сутки")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(MapMessages.objects.count(), 2)

    def test_cooldown_does_not_apply_to_moderators_and_curators(self):
        for suffix, role in [("mod", User.ROLE_MODERATOR), ("curator", User.ROLE_CURATOR)]:
            with self.subTest(role=role):
                _login(self.client, _create_user(suffix, roles=[role]))
                self._post()

                response = self._post(text="И ещё одно")

                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()["can_post"])

    def test_cooldown_is_personal(self):
        self._post()
        _login(self.client, _create_user("another_author"))

        response = self._post(text="Я тут впервые")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(MapMessages.objects.count(), 2)


class TestVisibleMapMessages(TestCase):
    def setUp(self):
        self.user = _create_user("visible_viewer")

    def _create(self, text, created_at, upvotes=0):
        message = MapMessages.objects.create(
            author=self.user, text=text, latitude=1.0, longitude=1.0, upvotes=upvotes
        )
        MapMessages.objects.filter(id=message.id).update(created_at=created_at)  # auto_now_add ignores kwargs
        return message

    @patch.object(MapMessages, "MAX_MESSAGES_ON_MAP", 2)
    def test_shows_only_the_latest_messages(self):
        now = datetime.utcnow()
        newest = self._create("новое", now)
        newer = self._create("посвежее", now - timedelta(days=1))
        self._create("старое", now - timedelta(days=2))

        visible = MapMessages.visible_for_user(self.user)

        self.assertEqual({message.id for message in visible}, {newest.id, newer.id})

    @patch.object(MapMessages, "MAX_MESSAGES_ON_MAP", 1)
    def test_shows_popular_messages_no_matter_how_old(self):
        now = datetime.utcnow()
        newest = self._create("новое", now)
        popular = self._create(
            "древнее, но популярное", now - timedelta(days=100), upvotes=MapMessages.POPULAR_UPVOTES + 1
        )
        self._create("просто старое", now - timedelta(days=100), upvotes=MapMessages.POPULAR_UPVOTES)

        visible = MapMessages.visible_for_user(self.user)

        self.assertEqual({message.id for message in visible}, {newest.id, popular.id})


class TestUpvoteMapMessage(TestCase):
    def setUp(self):
        self.author = _create_user("vote_author")
        self.voter = _create_user("voter")
        self.message = MapMessages.objects.create(
            author=self.author, text="Хорошее сообщение", latitude=1.0, longitude=2.0
        )
        self.url = f"/map/messages/{self.message.id}/upvote.json"
        _login(self.client, self.voter)

    def test_counts_the_vote_and_stores_it(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"upvotes": 1, "is_voted": True})

        self.message.refresh_from_db()
        self.assertEqual(self.message.upvotes, 1)
        vote = MapMessageVote.objects.get()
        self.assertEqual(vote.user, self.voter)
        self.assertEqual(vote.message, self.message)

    def test_counts_every_user_only_once(self):
        self.client.post(self.url)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["upvotes"], 1)

        self.message.refresh_from_db()
        self.assertEqual(self.message.upvotes, 1)
        self.assertEqual(MapMessageVote.objects.count(), 1)

    def test_counts_votes_of_different_users(self):
        self.client.post(self.url)

        another_voter = _create_user("another_voter")
        _login(self.client, another_voter)
        response = self.client.post(self.url)

        self.assertEqual(response.json()["upvotes"], 2)
        self.message.refresh_from_db()
        self.assertEqual(self.message.upvotes, 2)

    def test_rejects_votes_for_own_messages(self):
        _login(self.client, self.author)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(MapMessageVote.objects.exists())
        self.message.refresh_from_db()
        self.assertEqual(self.message.upvotes, 0)

    def test_rejects_get_requests(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)
        self.assertFalse(MapMessageVote.objects.exists())

    def test_requires_auth(self):
        self.client.cookies.clear()

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(MapMessageVote.objects.exists())

    def test_fails_on_unknown_messages(self):
        # the api decorator turns every exception, 404 included, into its own error response
        response = self.client.post("/map/messages/8ab5a3cf-3f5e-4f8a-9e6f-3e1b4a3d2c1b/upvote.json")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(MapMessageVote.objects.exists())


class TestMapMessagesGeoJson(TestCase):
    def setUp(self):
        self.user = _create_user("geojson_author", avatar="https://example.com/a.jpg")

    def test_serializes_messages_into_feature_collection(self):
        MapMessages.objects.create(author=self.user, text="Первое", latitude=1.5, longitude=2.5)
        MapMessages.objects.create(author=self.user, text="Второе", latitude=3.5, longitude=4.5)

        geojson = json.loads(map_messages_geo_json(MapMessages.objects.all()))

        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertEqual({f["properties"]["text"] for f in geojson["features"]}, {"Первое", "Второе"})
        self.assertEqual(
            geojson["features"][0]["properties"]["author_avatar"], "https://example.com/a.jpg"
        )

    def test_marks_messages_the_user_wrote_or_already_voted_for(self):
        voter = _create_user("geojson_voter")
        mine = MapMessages.objects.create(author=voter, text="Моё", latitude=1.0, longitude=1.0)
        voted = MapMessages.objects.create(author=self.user, text="За это я голосовал", latitude=2.0, longitude=2.0)
        untouched = MapMessages.objects.create(author=self.user, text="Чужое", latitude=3.0, longitude=3.0)
        MapMessageVote.upvote(user=voter, message=voted)

        geojson = json.loads(map_messages_geo_json(MapMessages.objects_for_user(voter), voter))
        properties = {f["properties"]["id"]: f["properties"] for f in geojson["features"]}

        self.assertTrue(properties[str(mine.id)]["is_mine"])
        self.assertFalse(properties[str(mine.id)]["is_voted"])

        self.assertTrue(properties[str(voted.id)]["is_voted"])
        self.assertFalse(properties[str(voted.id)]["is_mine"])
        self.assertEqual(properties[str(voted.id)]["upvotes"], 1)

        self.assertFalse(properties[str(untouched.id)]["is_voted"])
        self.assertFalse(properties[str(untouched.id)]["is_mine"])
        self.assertEqual(properties[str(untouched.id)]["upvotes"], 0)
        self.assertEqual(
            properties[str(untouched.id)]["upvote_url"], f"/map/messages/{untouched.id}/upvote.json"
        )


class TestPeoplePageRendersMessages(TestCase):
    def setUp(self):
        self.user = _create_user("page_viewer")
        _login(self.client, self.user)

    def test_message_text_is_escaped_in_the_component_prop(self):
        MapMessages.objects.create(
            author=self.user,
            text="""it's "quoted" <script>alert(1)</script> {{ 1 + 1 }}""",
            latitude=10.0,
            longitude=20.0,
        )

        content = self.client.get("/people/").content.decode()

        # the raw characters would break out of the html attribute and the vue template
        self.assertNotIn("<script>alert(1)</script>", content)
        self.assertIn("&lt;script&gt;", content)
        self.assertIn("&#x27;", content)
        self.assertIn("create-message-url=\"/map/messages/create.json\"", content)
