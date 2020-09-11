from datetime import datetime, timedelta
import json
from urllib.parse import urljoin

import django
from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse
from django.http.response import HttpResponseNotAllowed, HttpResponseBadRequest
from django_q import brokers
from django_q.signing import SignedPackage
import jwt
from unittest import skip

django.setup()  # todo: how to run tests from PyCharm without this workaround?

from .models import Code, Session
from club.exceptions import RateLimitException, InvalidCode
from users.models.user import User


class HelperClient(Client):

    def __init__(self, user=None):
        super(HelperClient, self).__init__()
        self.user = user

    def authorise(self):
        if not self.user:
            raise ValueError('Missed `user` property to use this method')

        session = Session.create_for_user(self.user)
        self.cookies["token"] = session.token
        self.cookies["token"]["expires"] = datetime.utcnow() + timedelta(days=30)
        self.cookies["token"]['httponly'] = True
        self.cookies["token"]['secure'] = True

        return self

    @staticmethod
    def is_response_contain(response, text):
        content = response.content
        if not isinstance(text, bytes):
            text = str(text)
            content = content.decode(response.charset)

        real_count = content.count(text)
        return real_count != 0

    def is_authorised(self) -> bool:
        response = self.get(reverse('debug_api_me'))
        content = response.content.decode(response.charset)
        content_dict = json.loads(content)

        return content_dict["is_authorised"]

    def print_me(self):
        response = self.get(reverse('debug_api_me'))
        content = response.content.decode(response.charset)
        content_dict = json.loads(content)

        return content_dict

    @staticmethod
    def is_access_denied(response):
        return HelperClient.is_response_contain(response, text="Эта страница доступна только участникам Клуба")


class CodeModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up data for the whole TestCase
        cls.new_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
        )

    def test_create_code_positive(self):
        recipient = "success@a.com"

        code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)
        self.assertEqual(code.recipient, recipient)
        self.assertEqual(self.new_user.id, code.user_id)
        self.assertEqual(len(code.code), settings.AUTH_CODE_LENGTH)
        self.assertAlmostEqual(code.expires_at.second, (datetime.utcnow() + timedelta(minutes=15)).second, delta=5)

    def test_create_code_ratelimit(self):
        recipient = "ratelimit@a.com"

        # override the AUTH_MAX_CODE_TIMEDELTA setting
        with self.settings(AUTH_MAX_CODE_COUNT=1):
            code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)
            self.assertEqual(len(code.code), settings.AUTH_CODE_LENGTH)

            # second attempt should rise exception
            with self.assertRaises(RateLimitException):
                Code.create_for_user(user=self.new_user, recipient=recipient)

    def test_create_code_reset_ratelimit(self):
        recipient = "ratelimit@a.com"

        with self.settings(AUTH_MAX_CODE_COUNT=1):
            code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)
            self.assertEqual(len(code.code), settings.AUTH_CODE_LENGTH)

            # move creation time to deep enough past
            code.created_at = datetime.utcnow() - settings.AUTH_MAX_CODE_TIMEDELTA - timedelta(seconds=1)
            code.save()

            # no exception raises
            code = Code.create_for_user(user=self.new_user, recipient=recipient)
            self.assertEqual(len(code.code), settings.AUTH_CODE_LENGTH)

    def test_check_code_positive(self):
        recipient = "success@a.com"
        code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)

        user = Code.check_code(recipient=recipient, code=code.code)

        self.assertEqual(user.id, self.new_user.id)

    def test_check_code_which_is_incorrect(self):
        with self.assertRaises(InvalidCode):
            Code.check_code(recipient="failed@xxx.com", code="failed")

    def test_check_code_twice(self):
        recipient = "success@a.com"
        code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)
        Code.check_code(recipient=recipient, code=code.code)  # activate first time

        with self.assertRaises(InvalidCode):
            Code.check_code(recipient=recipient, code=code.code)

    def test_check_code_which_is_not_last_one(self):
        # issue few codes
        recipient = "fewcodes@a.com"
        code1: Code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)
        code2: Code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)
        # for stability test runs
        code2.created_at -= timedelta(seconds=1)
        code2.save()

        with self.assertRaises(InvalidCode):
            Code.check_code(recipient=recipient, code=code2.code)

        # first one is successful
        user = Code.check_code(recipient=recipient, code=code1.code)
        self.assertEqual(user.id, self.new_user.id)

    def test_check_code_which_is_for_other_user(self):
        recipient_right = "true-user@a.com"
        recipient_wrong = "wrong-user@x.com"
        code = Code.create_for_user(user=self.new_user, recipient=recipient_right, length=settings.AUTH_CODE_LENGTH)

        with self.assertRaises(InvalidCode):
            Code.check_code(recipient=recipient_wrong, code=code.code)

    def test_check_code_when_exceeded_attempts_count(self):
        recipient = "exceeded_attemts@a.com"
        code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)

        # override the AUTH_MAX_CODE_TIMEDELTA setting
        with self.settings(AUTH_MAX_CODE_ATTEMPTS=1):
            # first attempt
            with self.assertRaises(InvalidCode):
                Code.check_code(recipient=recipient, code="wrong_attempt")

            # second attempt should rise ratelimit exception
            with self.assertRaises(RateLimitException):
                Code.check_code(recipient=recipient, code=code.code)

    def test_check_code_which_is_expired(self):
        recipient = "expired@a.com"
        code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)
        code.expires_at = datetime.utcnow() - timedelta(seconds=1)
        code.save()

        with self.assertRaises(InvalidCode):
            Code.check_code(recipient=recipient, code=code.code)


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


class TestEmailLoginView(TestCase):
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
        self.assertContains(response=response, text="Такого юзера нет 🤔", status_code=200)

    def test_secret_hash_login(self):
        response = self.client.post(reverse('email_login'),
                                    data={'email_or_login': self.new_user.secret_auth_code, })

        self.assertRedirects(response=response, expected_url=f'/user/{self.new_user.slug}/',
                             fetch_redirect_response=False)
        self.assertTrue(self.client.is_authorised())

    def test_secret_hash_user_not_exist(self):
        response = self.client.post(reverse('email_login'),
                                    data={'email_or_login': 'not-existed@user.com|-xxx', })
        self.assertContains(response=response, text="Такого юзера нет 🤔", status_code=200)

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


class TestEmailLoginCodeView(TestCase):
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


class TestExternalLoginView(TestCase):
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
        self.client = HelperClient()

    def test_successful_flat_redirect(self):
        # given
        self.client = HelperClient(user=self.new_user)
        self.client.authorise()

        # when
        with self.settings(JWT_SECRET="xxx"):
            response = self.client.get(reverse('external_login'), data={'redirect': 'some-page'})

        # then
        self.assertRegex(text=urljoin(response.request['PATH_INFO'], response.url),
                         expected_regex='\/auth\/external\/some-page\?jwt=.*')

        # check jwt
        url_params = response.url.split("?")[1]
        jwt_str = url_params.split("=")[1]
        payload = jwt.decode(jwt_str, key="xxx", verify=True)
        self.assertIsNotNone(payload)
        self.assertEqual(payload['user_slug'], self.new_user.slug)
        self.assertEqual(payload['user_name'], self.new_user.full_name)
        self.assertIsNotNone(payload['exp'])

    def test_successful_redirect_with_query_params(self):
        # given
        self.client = HelperClient(user=self.new_user)
        self.client.authorise()

        # when
        with self.settings(JWT_SECRET="xxx"):
            response = self.client.get(reverse('external_login'), data={'redirect': 'some-page?param1=value1'})

        # then
        self.assertRegex(text=urljoin(response.request['PATH_INFO'], response.url),
                         expected_regex='\/auth\/external\/some-page\?param1=value1&jwt=.*')

    def test_param_redirect_absent(self):
        response = self.client.get(reverse('external_login'))
        self.assertContains(response=response, text="Нужен параметр ?redirect", status_code=200)

    def test_user_is_unauthorised(self):
        response = self.client.get(reverse('external_login'), data={'redirect': 'some-page'})
        self.assertRedirects(response=response,
                             expected_url='/auth/login/?goto=%2Fauth%2Fexternal%2F%3Fredirect%3Dsome-page',
                             fetch_redirect_response=False)

        self.assertFalse(self.client.is_authorised())


class TestPatreonLoginView(TestCase):
    def test_positive(self):
        with self.settings(PATREON_CLIENT_ID="x-client_id",
                           PATREON_REDIRECT_URL="http://x-redirect_url.com",
                           PATREON_SCOPE="x-scope"):
            response = self.client.get(reverse('patreon_login'), )
            self.assertRedirects(response=response,
                                 expected_url='https://www.patreon.com/oauth2/authorize?client_id=x-client_id&redirect_uri=http%3A%2F%2Fx-redirect_url.com&response_type=code&scope=x-scope',
                                 fetch_redirect_response=False)
