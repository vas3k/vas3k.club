from unittest.mock import patch

from django.test import Client, TestCase, override_settings, RequestFactory
from django.urls import reverse

from debug.utils_for_tests import create_approved_user, login
from users.views.settings import request_data


class TestUserSettingsViews(TestCase):
    def setUp(self):
        self.user = create_approved_user("settings_owner")
        self.other = create_approved_user("settings_other")
        self.client = Client()
        self.factory = RequestFactory()

    def test_non_owner_cannot_access_edit_notifications(self):
        login(self.client, self.other)

        response = self.client.get(reverse("edit_notifications", args=[self.user.slug]))

        self.assertEqual(response.status_code, 404)

    def test_edit_account_regenerate_changes_secret_hash(self):
        login(self.client, self.user)
        before = self.user.secret_hash

        response = self.client.post(reverse("edit_account", args=[self.user.slug]), data={"regenerate": "1"})

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.secret_hash, before)

    def test_request_data_get_redirects_to_edit_data(self):
        login(self.client, self.user)

        response = self.client.get(reverse("request_user_data", args=[self.user.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("edit_data", args=[self.user.slug]))

    @override_settings(DEBUG=False)
    @patch("users.views.settings.async_task")
    @patch("users.views.settings.DataRequests.register_archive_request")
    def test_request_data_post_enqueues_async_job(self, mock_register, mock_async_task):
        login(self.client, self.user)

        response = self.client.post(reverse("request_user_data", args=[self.user.slug]))

        self.assertEqual(response.status_code, 200)
        mock_register.assert_called_once_with(self.user)
        mock_async_task.assert_called_once()

    @patch("users.views.settings.settings.DEBUG", True)
    @patch("users.views.settings.generate_data_archive")
    @patch("users.views.settings.DataRequests.register_archive_request")
    def test_request_data_post_calls_sync_generator_in_debug(self, mock_register, mock_generate):
        request = self.factory.post(reverse("request_user_data", args=[self.user.slug]))
        request.me = self.user

        response = request_data(request, self.user.slug)
        self.assertEqual(response.status_code, 200)
        mock_register.assert_called_once_with(self.user)
        mock_generate.assert_called_once_with(self.user)
