import unittest
import uuid
from datetime import datetime, timedelta

import django
from django.test import TestCase
from django.urls import reverse
from django.http.response import HttpResponseNotAllowed, HttpResponseBadRequest
from django_q import brokers
from django_q.signing import SignedPackage
from unittest import skip
from unittest.mock import patch

django.setup()  # todo: how to run tests from PyCharm without this workaround?

from authn.models.session import Code
from authn.providers.common import Membership, Platform
from authn.exceptions import PatreonException
from club import features
from debug.helpers import HelperClient, JWT_STUB_VALUES
from users.models.user import User


class ViewsAuthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up data for the whole TestCase
        cls.new_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            slug="ujlbu4"
        )

    def setUp(self):
        self.client = HelperClient(user=self.new_user)

    def test_join_anonymous(self):
        response = self.client.get(reverse("join"))
        # check auth/join.html is rendered
        self.assertContains(response=response, text="Всегда рады новым членам", status_code=200)

    def test_join_authorised(self):
        self.client.authorise()

        response = self.client.get(reverse("join"))
        self.assertRedirects(response=response, expected_url=f"/user/{self.new_user.slug}/",
                             fetch_redirect_response=False)

    def test_login_anonymous(self):
        response = self.client.get(reverse("login"))
        # check auth/join.html is rendered
        self.assertContains(response=response, text="Вход по почте или нику", status_code=200)

    def test_login_authorised(self):
        self.client.authorise()

        response = self.client.get(reverse("login"))
        self.assertRedirects(response=response, expected_url=f"/user/{self.new_user.slug}/",
                             fetch_redirect_response=False)

    def test_logout_success(self):
        self.client.authorise()

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response=response, expected_url=f"/", fetch_redirect_response=False)
        self.assertFalse(self.client.is_authorised())

    def test_logout_unauthorised(self):
        response = self.client.post(reverse("logout"))
        self.assertTrue(self.client.is_access_denied(response))
        self.assertFalse(self.client.is_authorised())

    def test_logout_wrong_method(self):
        self.client.authorise()

        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, HttpResponseNotAllowed.status_code)

        response = self.client.put(reverse("logout"))
        self.assertEqual(response.status_code, HttpResponseNotAllowed.status_code)

        response = self.client.delete(reverse("logout"))
        self.assertEqual(response.status_code, HttpResponseNotAllowed.status_code)

    def test_debug_dev_login_unauthorised(self):
        response = self.client.post(reverse("debug_dev_login"))
        self.assertTrue(self.client.is_authorised())

        me = self.client.print_me()
        self.assertIsNotNone(me["id"])
        self.assertEqual(me["email"], "dev@dev.dev")
        self.assertTrue(me["is_email_verified"])
        self.assertTrue(me["slug"], "dev")
        self.assertEqual(me["moderation_status"], "approved")
        self.assertEqual(me["roles"], ["god"])
        # todo: check created post (intro)

    def test_debug_dev_login_authorised(self):
        self.client.authorise()

        response = self.client.post(reverse("debug_dev_login"))
        self.assertTrue(self.client.is_authorised())

        me = self.client.print_me()
        self.assertTrue(me["slug"], self.new_user.slug)

    def test_debug_random_login_unauthorised(self):
        response = self.client.post(reverse("debug_random_login"))
        self.assertTrue(self.client.is_authorised())

        me = self.client.print_me()
        self.assertIsNotNone(me["id"])
        self.assertIn("@random.dev", me["email"])
        self.assertTrue(me["is_email_verified"])
        self.assertEqual(me["moderation_status"], "approved")
        self.assertEqual(me["roles"], [])
        # todo: check created post (intro)


class ViewEmailLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up data for the whole TestCase
        cls.new_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            slug="ujlbu4"
        )

        cls.broker = brokers.get_broker()
        cls.assertTrue(cls.broker.ping(), "broker is not available")

    def setUp(self):
        self.client = HelperClient(user=self.new_user)

        self.broker.purge_queue()

    def test_login_by_email_positive(self):
        # when
        response = self.client.post(reverse("email_login"),
                                    data={"email_or_login": self.new_user.email, })

        # then
        self.assertContains(response=response, text="Вам отправлен код!", status_code=200)
        issued_code = Code.objects.filter(recipient=self.new_user.email).get()
        self.assertIsNotNone(issued_code)

        # check email was sent
        packages = self.broker.dequeue()
        task_signed = packages[0][1]
        task = SignedPackage.loads(task_signed)
        self.assertEqual(task["func"].__name__, "send_auth_email")
        self.assertEqual(task["args"][0].id, self.new_user.id)
        self.assertEqual(task["args"][1].id, issued_code.id)

        # check notify wast sent
        packages = self.broker.dequeue()
        task_signed = packages[0][1]
        task = SignedPackage.loads(task_signed)
        self.assertEqual(task["func"].__name__, "notify_user_auth")
        self.assertEqual(task["args"][0].id, self.new_user.id)
        self.assertEqual(task["args"][1].id, issued_code.id)

        # it"s not yet authorised, only code was sent
        self.assertFalse(self.client.is_authorised())

    def test_login_user_not_exist(self):
        response = self.client.post(reverse("email_login"),
                                    data={"email_or_login": "not-existed@user.com", })
        self.assertContains(response=response, text="Такого юзера нет 🤔", status_code=404)

    def test_email_login_missed_input_data(self):
        response = self.client.post(reverse("email_login"), data={})
        self.assertRedirects(response=response, expected_url=f"/auth/login/",
                             fetch_redirect_response=False)

    def test_email_login_wrong_method(self):
        response = self.client.get(reverse("email_login"))
        self.assertRedirects(response=response, expected_url=f"/auth/login/",
                             fetch_redirect_response=False)

        response = self.client.put(reverse("email_login"))
        self.assertRedirects(response=response, expected_url=f"/auth/login/",
                             fetch_redirect_response=False)

        response = self.client.delete(reverse("email_login"))
        self.assertRedirects(response=response, expected_url=f"/auth/login/",
                             fetch_redirect_response=False)


class ViewEmailLoginCodeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up data for the whole TestCase
        cls.new_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            slug="ujlbu4"
        )
        cls.code = Code.create_for_user(user=cls.new_user, recipient=cls.new_user.email)

    def setUp(self):
        self.client = HelperClient(user=self.new_user)

    def test_correct_code(self):
        # given
        # email is not verified yet
        self.assertFalse(User.objects.get(id=self.new_user.id).is_email_verified)

        # when
        response = self.client.get(reverse("email_login_code"),
                                   data={"email": self.new_user.email, "code": self.code.code})

        self.assertRedirects(response=response, expected_url=f"/user/{self.new_user.slug}/",
                             fetch_redirect_response=False)
        self.assertTrue(self.client.is_authorised())
        self.assertTrue(User.objects.get(id=self.new_user.id).is_email_verified)

    def test_empty_params(self):
        response = self.client.get(reverse("email_login_code"), data={})
        self.assertRedirects(response=response, expected_url=f"/auth/login/",
                             fetch_redirect_response=False)
        self.assertFalse(self.client.is_authorised())
        self.assertFalse(User.objects.get(id=self.new_user.id).is_email_verified)

    def test_wrong_code(self):
        response = self.client.get(reverse("email_login_code"),
                                   data={"email": self.new_user.email, "code": "intentionally-wrong-code"})

        self.assertEqual(response.status_code, HttpResponseBadRequest.status_code)
        self.assertFalse(self.client.is_authorised())
        self.assertFalse(User.objects.get(id=self.new_user.id).is_email_verified)

@unittest.skipIf(not features.PATREON_AUTH_ENABLED, reason="Patreon auth was disabled")
class ViewPatreonLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up data for the whole TestCase
        cls.new_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            slug="ujlbu4"
        )

    def test_positive(self):
        self.client = HelperClient(user=self.new_user)
        self.client.authorise()
        with self.settings(PATREON_CLIENT_ID="x-client_id",
                           PATREON_REDIRECT_URL="http://x-redirect_url.com",
                           PATREON_SCOPE="x-scope"):
            response = self.client.get(reverse("patreon_sync"), )
            self.assertRedirects(response=response,
                                 expected_url="https://www.patreon.com/oauth2/authorize?client_id=x-client_id&redirect_uri=http%3A%2F%2Fx-redirect_url.com&response_type=code&scope=x-scope",
                                 fetch_redirect_response=False)


@unittest.skipIf(not features.PATREON_AUTH_ENABLED, reason="Patreon auth was disabled")
@patch("authn.views.patreon.patreon")
class ViewPatreonOauthCallbackTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up data for the whole TestCase
        cls.new_user: User = User.objects.create(
            email="existed-user@email.com",
            patreon_id="12345",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            slug="ujlbu4"
        )

    def setUp(self):
        self.client = HelperClient(user=self.new_user)
        self.client.authorise()

        self.stub_patreon_response_oauth_token = {
            "access_token": "xxx-access-token",
            "refresh_token": "xxx-refresh-token",
            "expires_in": (datetime.utcnow() + timedelta(minutes=5)).microsecond,
            "scope": "scope??",
            "token_type": "Bearer"
        }
        self.stub_patreon_response_oauth_identity = None  # doesn"t need for now
        self.stub_parse_membership = Membership(
            platform=Platform.patreon,
            user_id="12345",
            full_name="PatreonMember FullName",
            email="platform@patreon.com",
            image="http://xxx.url",
            started_at=datetime.utcnow(),
            charged_at=None,
            expires_at=datetime.utcnow() + timedelta(days=100 * 365),
            lifetime_support_cents=400,
            currently_entitled_amount_cents=0
        )

    def test_patreon_new_member_error(self, mocked_patreon):
        # given
        mocked_patreon.fetch_auth_data.return_value = self.stub_patreon_response_oauth_token
        mocked_patreon.fetch_user_data.return_value = self.stub_patreon_response_oauth_identity
        membership = self.stub_parse_membership
        membership.user_id = str(uuid.uuid4())
        membership.email = f"{membership.user_id}@email.com"
        mocked_patreon.parse_active_membership.return_value = membership

        # when
        response = self.client.get(reverse("patreon_sync_callback"), data={"code": "1234"})

        # then
        self.assertContains(response=response, text="Ваш email не совпадает",
                            status_code=400)
        created_user: User = User.objects.filter(email=membership.email).first()
        self.assertIsNone(created_user)

    def test_successful_login_existed_member(self, mocked_patreon):
        # given
        mocked_patreon.fetch_auth_data.return_value = self.stub_patreon_response_oauth_token
        mocked_patreon.fetch_user_data.return_value = self.stub_patreon_response_oauth_identity
        membership = self.stub_parse_membership
        membership.email = "existed-user@email.com"
        membership.user_id = "12345"
        membership.lifetime_support_cents = 100500
        mocked_patreon.parse_active_membership.return_value = membership

        # when
        response = self.client.get(reverse("patreon_sync_callback"), data={"code": "1234"})

        # then
        self.assertRedirects(response=response, expected_url=f"/user/ujlbu4/",
                             fetch_redirect_response=False)
        self.assertTrue(self.client.is_authorised())
        # user updated attributes
        created_user: User = User.objects.filter(patreon_id="12345").get()
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.membership_expires_at, membership.expires_at)

    def test_patreon_exception(self, mocked_patreon):
        # given
        mocked_patreon.fetch_auth_data.side_effect = PatreonException("custom_test_exception")

        # when
        response = self.client.get(reverse("patreon_sync_callback"), data={"code": "1234"})

        # then
        self.assertContains(response=response, text="Не получилось загрузить ваш профиль с серверов патреона",
                            status_code=504)

    def test_patreon_not_membership(self, mocked_patreon):
        # given
        mocked_patreon.fetch_auth_data.return_value = self.stub_patreon_response_oauth_token
        mocked_patreon.fetch_user_data.return_value = None
        mocked_patreon.parse_active_membership.return_value = None  # no membership

        # when
        response = self.client.get(reverse("patreon_sync_callback"), data={"code": "1234"})

        # then
        self.assertContains(response=response, text="Надо быть патроном, чтобы состоять в Клубе", status_code=402)

    def test_param_code_absent(self, mocked_patreon=None):
        response = self.client.get(reverse("patreon_sync_callback"), data={})
        self.assertContains(response=response, text="Что-то сломалось между нами и патреоном", status_code=500)
