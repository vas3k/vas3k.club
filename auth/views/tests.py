from datetime import datetime, timedelta
from urllib.parse import urljoin
import uuid

import django
from django.test import TestCase
from django.urls import reverse
from django.http.response import HttpResponseNotAllowed, HttpResponseBadRequest
from django_q import brokers
from django_q.signing import SignedPackage
import jwt
from unittest import skip
from unittest.mock import patch

django.setup()  # todo: how to run tests from PyCharm without this workaround?

from auth.models import Code, Apps
from auth.providers.common import Membership, Platform
from auth.exceptions import PatreonException
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
        response = self.client.get(reverse('join'))
        # check auth/join.html is rendered
        self.assertContains(response=response, text="Всегда рады новым членам", status_code=200)

    def test_join_authorised(self):
        self.client.authorise()

        response = self.client.get(reverse('join'))
        self.assertRedirects(response=response, expected_url=f'/user/{self.new_user.slug}/',
                             fetch_redirect_response=False)

    def test_login_anonymous(self):
        response = self.client.get(reverse('login'))
        # check auth/join.html is rendered
        self.assertContains(response=response, text="Вход по почте или нику", status_code=200)

    def test_login_authorised(self):
        self.client.authorise()

        response = self.client.get(reverse('login'))
        self.assertRedirects(response=response, expected_url=f'/user/{self.new_user.slug}/',
                             fetch_redirect_response=False)

    def test_logout_success(self):
        self.client.authorise()

        response = self.client.post(reverse('logout'))

        self.assertRedirects(response=response, expected_url=f'/', fetch_redirect_response=False)
        self.assertFalse(self.client.is_authorised())

    def test_logout_unauthorised(self):
        response = self.client.post(reverse('logout'))
        self.assertTrue(self.client.is_access_denied(response))

    def test_logout_wrong_method(self):
        self.client.authorise()

        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, HttpResponseNotAllowed.status_code)

        response = self.client.put(reverse('logout'))
        self.assertEqual(response.status_code, HttpResponseNotAllowed.status_code)

        response = self.client.delete(reverse('logout'))
        self.assertEqual(response.status_code, HttpResponseNotAllowed.status_code)

    def test_debug_dev_login_unauthorised(self):
        response = self.client.post(reverse('debug_dev_login'))
        self.assertTrue(self.client.is_authorised())

        me = self.client.print_me()
        self.assertIsNotNone(me['id'])
        self.assertEqual(me['email'], 'dev@dev.dev')
        self.assertTrue(me['is_email_verified'])
        self.assertTrue(me['slug'], 'dev')
        self.assertEqual(me['moderation_status'], 'approved')
        self.assertEqual(me['roles'], ['god'])
        # todo: check created post (intro)

    def test_debug_dev_login_authorised(self):
        self.client.authorise()

        response = self.client.post(reverse('debug_dev_login'))
        self.assertTrue(self.client.is_authorised())

        me = self.client.print_me()
        self.assertTrue(me['slug'], self.new_user.slug)

    def test_debug_random_login_unauthorised(self):
        response = self.client.post(reverse('debug_random_login'))
        self.assertTrue(self.client.is_authorised())

        me = self.client.print_me()
        self.assertIsNotNone(me['id'])
        self.assertIn('@random.dev', me['email'])
        self.assertTrue(me['is_email_verified'])
        self.assertEqual(me['moderation_status'], 'approved')
        self.assertEqual(me['roles'], [])
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
        cls.assertTrue(cls.broker.ping(), 'broker is not available')

    def setUp(self):
        self.client = HelperClient(user=self.new_user)

        self.broker.purge_queue()

    def test_login_by_email_positive(self):
        # when
        response = self.client.post(reverse('email_login'),
                                    data={'email_or_login': self.new_user.email, })

        # then
        self.assertContains(response=response, text="Вам отправлен код!", status_code=200)
        issued_code = Code.objects.filter(recipient=self.new_user.email).get()
        self.assertIsNotNone(issued_code)

        # check email was sent
        packages = self.broker.dequeue()
        task_signed = packages[0][1]
        task = SignedPackage.loads(task_signed)
        self.assertEqual(task['func'].__name__, 'send_auth_email')
        self.assertEqual(task['args'][0].id, self.new_user.id)
        self.assertEqual(task['args'][1].id, issued_code.id)

        # check notify wast sent
        packages = self.broker.dequeue()
        task_signed = packages[0][1]
        task = SignedPackage.loads(task_signed)
        self.assertEqual(task['func'].__name__, 'notify_user_auth')
        self.assertEqual(task['args'][0].id, self.new_user.id)
        self.assertEqual(task['args'][1].id, issued_code.id)

        # it's not yet authorised, only code was sent
        self.assertFalse(self.client.is_authorised())

    def test_login_user_not_exist(self):
        response = self.client.post(reverse('email_login'),
                                    data={'email_or_login': 'not-existed@user.com', })
        self.assertContains(response=response, text="Такого юзера нет 🤔", status_code=404)

    def test_secret_hash_login(self):
        response = self.client.post(reverse('email_login'),
                                    data={'email_or_login': self.new_user.secret_auth_code, })

        self.assertRedirects(response=response, expected_url=f'/user/{self.new_user.slug}/',
                             fetch_redirect_response=False)
        self.assertTrue(self.client.is_authorised())

    def test_secret_hash_user_not_exist(self):
        response = self.client.post(reverse('email_login'),
                                    data={'email_or_login': 'not-existed@user.com|-xxx', })
        self.assertContains(response=response, text="Такого юзера нет 🤔", status_code=404)

    @skip("todo")
    def test_secret_hash_cancel_user_deletion(self):
        # todo: mark user as deleted
        self.assertTrue(False)

    def test_email_login_missed_input_data(self):
        response = self.client.post(reverse('email_login'), data={})
        self.assertRedirects(response=response, expected_url=f'/auth/login/',
                             fetch_redirect_response=False)

    def test_email_login_wrong_method(self):
        response = self.client.get(reverse('email_login'))
        self.assertRedirects(response=response, expected_url=f'/auth/login/',
                             fetch_redirect_response=False)

        response = self.client.put(reverse('email_login'))
        self.assertRedirects(response=response, expected_url=f'/auth/login/',
                             fetch_redirect_response=False)

        response = self.client.delete(reverse('email_login'))
        self.assertRedirects(response=response, expected_url=f'/auth/login/',
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
        response = self.client.get(reverse('email_login_code'),
                                   data={'email': self.new_user.email, 'code': self.code.code})

        self.assertRedirects(response=response, expected_url=f'/user/{self.new_user.slug}/',
                             fetch_redirect_response=False)
        self.assertTrue(self.client.is_authorised())
        self.assertTrue(User.objects.get(id=self.new_user.id).is_email_verified)

    def test_empty_params(self):
        response = self.client.get(reverse('email_login_code'), data={})
        self.assertRedirects(response=response, expected_url=f'/auth/login/',
                             fetch_redirect_response=False)
        self.assertFalse(self.client.is_authorised())
        self.assertFalse(User.objects.get(id=self.new_user.id).is_email_verified)

    def test_wrong_code(self):
        response = self.client.get(reverse('email_login_code'),
                                   data={'email': self.new_user.email, 'code': 'intentionally-wrong-code'})

        self.assertEqual(response.status_code, HttpResponseBadRequest.status_code)
        self.assertFalse(self.client.is_authorised())
        self.assertFalse(User.objects.get(id=self.new_user.id).is_email_verified)


class ViewExternalLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up data for the whole TestCase
        cls.new_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            slug="ujlbu4"
        )

        cls.app: Apps = Apps.objects.create(
            id="test",
            name="test",
            jwt_secret=JWT_STUB_VALUES.JWT_PRIVATE_KEY,
            jwt_algorithm="RS256",
            jwt_expire_hours=1,
            redirect_urls=["https://some-page"],
        )

    def setUp(self):
        self.client = HelperClient()

    def test_successful_flat_redirect(self):
        # given
        self.client = HelperClient(user=self.new_user)
        self.client.authorise()

        # when
        response = self.client.get(
            reverse('external_login'),
            data={
                'redirect': 'https://some-page',
                'app_id': 'test'
            }
        )

        # then
        self.assertRegex(text=urljoin(response.request['PATH_INFO'], response.url),
                         expected_regex='https://some-page\?jwt=.*')

        # check jwt
        url_params = response.url.split("?")[1]
        jwt_str = url_params.split("=")[1]
        payload = jwt.decode(jwt_str, verify=False)
        self.assertIsNotNone(payload)
        self.assertEqual(payload['user_slug'], self.new_user.slug)
        self.assertEqual(payload['user_name'], self.new_user.full_name)
        self.assertIsNotNone(payload['exp'])

    def test_successful_redirect_with_query_params(self):
        # given
        self.client = HelperClient(user=self.new_user)
        self.client.authorise()

        # when
        response = self.client.get(
            reverse('external_login'),
            data={
                'redirect': 'https://some-page?param1=value1',
                'app_id': 'test'
            }
        )

        # then
        self.assertRegex(text=urljoin(response.request['PATH_INFO'], response.url),
                         expected_regex='https://some-page\?param1=value1&jwt=.*')

    def test_param_wrong_app_id(self):
        self.client = HelperClient(user=self.new_user)
        self.client.authorise()
        response = self.client.get(reverse('external_login'), data={'app_id': 'UNKNOWN', 'redirect': 'https://some-page'})
        self.assertContains(response=response, text="Неизвестное приложение, проверьте параметр ?app_id", status_code=400)

    def test_param_redirect_absent(self):
        self.client = HelperClient(user=self.new_user)
        self.client.authorise()
        response = self.client.get(reverse('external_login'), data={'app_id': 'test'})
        self.assertContains(response=response, text="Нужен параметр ?redirect", status_code=400)

    def test_user_is_unauthorised(self):
        response = self.client.get(reverse('external_login'), data={'redirect': 'some-page', 'app_id': 'test'})
        self.assertRedirects(response=response,
                             expected_url='/auth/login/?goto=%2Fauth%2Fexternal%2F%3Fredirect%3Dsome-page',
                             fetch_redirect_response=False)

        self.assertFalse(self.client.is_authorised())


class ViewPatreonLoginTests(TestCase):
    def test_positive(self):
        with self.settings(PATREON_CLIENT_ID="x-client_id",
                           PATREON_REDIRECT_URL="http://x-redirect_url.com",
                           PATREON_SCOPE="x-scope"):
            response = self.client.get(reverse('patreon_login'), )
            self.assertRedirects(response=response,
                                 expected_url='https://www.patreon.com/oauth2/authorize?client_id=x-client_id&redirect_uri=http%3A%2F%2Fx-redirect_url.com&response_type=code&scope=x-scope',
                                 fetch_redirect_response=False)


@patch('auth.views.patreon.patreon')
class ViewPatreonOauthCallbackTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up data for the whole TestCase
        cls.new_user: User = User.objects.create(
            email="existed-user@email.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            slug="ujlbu4"
        )

    def setUp(self):
        self.client = HelperClient()

        self.stub_patreon_response_oauth_token = {
            "access_token": "xxx-access-token",
            "refresh_token": "xxx-refresh-token",
            "expires_in": (datetime.utcnow() + timedelta(minutes=5)).microsecond,
            "scope": "scope??",
            "token_type": "Bearer"
        }
        self.stub_patreon_response_oauth_identity = None  # doesn't need for now
        self.stub_parse_membership = Membership(
            platform=Platform.patreon,
            user_id=str(uuid.uuid4()),
            full_name="PatreonMember FullName",
            email="platform@patreon.com",
            image="http://xxx.url",
            started_at=datetime.utcnow(),
            charged_at=None,
            expires_at=datetime.utcnow() + timedelta(days=100 * 365),
            lifetime_support_cents=400,
            currently_entitled_amount_cents=0
        )

    def test_successful_login_new_member(self, mocked_patreon):
        # given
        mocked_patreon.fetch_auth_data.return_value = self.stub_patreon_response_oauth_token
        mocked_patreon.fetch_user_data.return_value = self.stub_patreon_response_oauth_identity
        membership = self.stub_parse_membership
        membership.user_id = str(uuid.uuid4())
        membership.email = f"{membership.user_id}@email.com"
        mocked_patreon.parse_active_membership.return_value = membership

        # when
        response = self.client.get(reverse('patreon_oauth_callback'), data={'code': '1234'})

        # then
        self.assertRedirects(response=response, expected_url=f'/user/PatreonMemberFullName/',
                             fetch_redirect_response=False)
        self.assertTrue(self.client.is_authorised())
        # created user
        created_user: User = User.objects.filter(email=membership.email).get()
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.patreon_id, membership.user_id)
        self.assertEqual(created_user.full_name, "PatreonMember FullName")
        self.assertEqual(created_user.membership_platform_type, "patreon")
        self.assertEqual(created_user.membership_started_at, membership.started_at)
        self.assertEqual(created_user.membership_expires_at, membership.expires_at)
        self.assertEqual(created_user.balance, 4)  # 400 / 100
        self.assertFalse(created_user.is_email_verified)
        self.assertEqual(created_user.membership_platform_data, {'access_token': 'xxx-access-token',
                                                                 'refresh_token': 'xxx-refresh-token'})

    def test_successful_login_existed_member(self, mocked_patreon):
        # given
        mocked_patreon.fetch_auth_data.return_value = self.stub_patreon_response_oauth_token
        mocked_patreon.fetch_user_data.return_value = self.stub_patreon_response_oauth_identity
        membership = self.stub_parse_membership
        membership.email = "existed-user@email.com"
        membership.lifetime_support_cents = 100500
        mocked_patreon.parse_active_membership.return_value = membership

        # when
        response = self.client.get(reverse('patreon_oauth_callback'), data={'code': '1234'})

        # then
        self.assertRedirects(response=response, expected_url=f'/user/ujlbu4/',
                             fetch_redirect_response=False)
        self.assertTrue(self.client.is_authorised())
        # user updated attributes
        created_user: User = User.objects.filter(email="existed-user@email.com").get()
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.membership_expires_at, membership.expires_at)
        self.assertEqual(created_user.balance, 1005)  # 100500 / 100
        self.assertEqual(created_user.membership_platform_data, {'access_token': 'xxx-access-token',
                                                                 'refresh_token': 'xxx-refresh-token'})

    def test_patreon_exception(self, mocked_patreon):
        # given
        mocked_patreon.fetch_auth_data.side_effect = PatreonException("custom_test_exception")

        # when
        response = self.client.get(reverse('patreon_oauth_callback'), data={'code': '1234'})

        # then
        self.assertContains(response=response, text="Не получилось загрузить ваш профиль с серверов патреона",
                            status_code=504)

    def test_patreon_not_membership(self, mocked_patreon):
        # given
        mocked_patreon.fetch_auth_data.return_value = self.stub_patreon_response_oauth_token
        mocked_patreon.fetch_user_data.return_value = None
        mocked_patreon.parse_active_membership.return_value = None  # no membership

        # when
        response = self.client.get(reverse('patreon_oauth_callback'), data={'code': '1234'})

        # then
        self.assertContains(response=response, text="Надо быть патроном, чтобы состоять в Клубе", status_code=402)

    def test_param_code_absent(self, mocked_patreon=None):
        response = self.client.get(reverse('patreon_oauth_callback'), data={})
        self.assertContains(response=response, text="Что-то сломалось между нами и патреоном", status_code=500)
