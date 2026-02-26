import os
import re
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import django
from django.test import TestCase

django.setup()

from gdpr.archive import generate_data_archive, delete_data_archive

MOCKED_TARGETS = [
    "gdpr.archive.dump_user_profile",
    "gdpr.archive.dump_user_posts",
    "gdpr.archive.dump_user_comments",
    "gdpr.archive.dump_user_bookmarks",
    "gdpr.archive.dump_user_upvotes",
    "gdpr.archive.dump_user_badges",
    "gdpr.archive.dump_user_achievements",
    "gdpr.archive.send_data_archive_ready_email",
    "gdpr.archive.schedule",
]


class GenerateDataArchiveTests(TestCase):

    def setUp(self):
        self.mocks = {}
        for target in MOCKED_TARGETS:
            name = target.rsplit(".", 1)[-1]
            patcher = patch(target)
            self.mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def _make_user():
        return SimpleNamespace(slug="testuser", email="test@example.com")

    def test_archive_filename_uses_csprng_token(self):
        user = self._make_user()
        with tempfile.TemporaryDirectory() as save_path:
            generate_data_archive(user, save_path=save_path)

            archives = [f for f in os.listdir(save_path) if f.endswith(".zip")]
            self.assertEqual(len(archives), 1)

            filename = archives[0]
            self.assertTrue(filename.startswith("testuser-"))

            token_part = filename.removeprefix("testuser-").removesuffix(".zip")
            self.assertGreaterEqual(len(token_part), 43)

    def test_archive_filename_not_predictable(self):
        user = self._make_user()
        with tempfile.TemporaryDirectory() as save_path:
            generate_data_archive(user, save_path=save_path)
            generate_data_archive(user, save_path=save_path)

            archives = sorted(os.listdir(save_path))
            self.assertEqual(len(archives), 2)
            self.assertNotEqual(archives[0], archives[1])

    def test_archive_filename_has_no_timestamp(self):
        user = self._make_user()
        with tempfile.TemporaryDirectory() as save_path:
            generate_data_archive(user, save_path=save_path)

            filename = os.listdir(save_path)[0]
            date_pattern = re.compile(r"\d{4}-\d{2}-\d{2}-\d{2}-\d{2}")
            self.assertIsNone(
                date_pattern.search(filename),
                f"Filename should not contain timestamp: {filename}",
            )

    def test_email_contains_download_url(self):
        user = self._make_user()
        with tempfile.TemporaryDirectory() as save_path:
            generate_data_archive(user, save_path=save_path)

            mock_email = self.mocks["send_data_archive_ready_email"]
            mock_email.assert_called_once()
            url = mock_email.call_args.kwargs["url"]
            self.assertTrue(url.startswith("/downloads/"))
            self.assertTrue(url.endswith(".zip"))

    def test_cleanup_scheduled(self):
        user = self._make_user()
        with tempfile.TemporaryDirectory() as save_path:
            generate_data_archive(user, save_path=save_path)

            mock_schedule = self.mocks["schedule"]
            mock_schedule.assert_called_once()
            self.assertEqual(
                mock_schedule.call_args[0][0],
                "gdpr.archive.delete_data_archive",
            )

    def test_archive_cleaned_up_on_schedule_failure(self):
        self.mocks["schedule"].side_effect = RuntimeError("queue down")
        user = self._make_user()
        with tempfile.TemporaryDirectory() as save_path:
            with self.settings(GDPR_ARCHIVE_STORAGE_PATH=save_path):
                with self.assertRaises(RuntimeError):
                    generate_data_archive(user, save_path=save_path)

            archives = [f for f in os.listdir(save_path) if f.endswith(".zip")]
            self.assertEqual(len(archives), 0)

    def test_archive_cleaned_up_on_email_failure(self):
        self.mocks["send_data_archive_ready_email"].side_effect = RuntimeError("smtp down")
        user = self._make_user()
        with tempfile.TemporaryDirectory() as save_path:
            with self.settings(GDPR_ARCHIVE_STORAGE_PATH=save_path):
                with self.assertRaises(RuntimeError):
                    generate_data_archive(user, save_path=save_path)

            archives = [f for f in os.listdir(save_path) if f.endswith(".zip")]
            self.assertEqual(len(archives), 0)


class DeleteDataArchiveTests(TestCase):

    def test_deletes_file_inside_archive_dir(self):
        with tempfile.TemporaryDirectory() as archive_dir:
            filepath = os.path.join(archive_dir, "test.zip")
            open(filepath, "w").close()

            with self.settings(GDPR_ARCHIVE_STORAGE_PATH=archive_dir):
                delete_data_archive(filepath)

            self.assertFalse(os.path.exists(filepath))

    def test_refuses_path_outside_archive_dir(self):
        with tempfile.TemporaryDirectory() as archive_dir, \
             tempfile.TemporaryDirectory() as other_dir:
            target = os.path.join(other_dir, "important.dat")
            open(target, "w").close()

            with self.settings(GDPR_ARCHIVE_STORAGE_PATH=archive_dir):
                delete_data_archive(target)

            self.assertTrue(os.path.exists(target))

    def test_refuses_path_traversal(self):
        with tempfile.TemporaryDirectory() as archive_dir:
            target = os.path.join(archive_dir, "..", "escaped.txt")
            real_target = os.path.realpath(target)
            open(real_target, "w").close()

            with self.settings(GDPR_ARCHIVE_STORAGE_PATH=archive_dir):
                delete_data_archive(target)

            self.assertTrue(os.path.exists(real_target))
            os.remove(real_target)

    def test_handles_already_deleted(self):
        with tempfile.TemporaryDirectory() as archive_dir:
            filepath = os.path.join(archive_dir, "gone.zip")

            with self.settings(GDPR_ARCHIVE_STORAGE_PATH=archive_dir):
                delete_data_archive(filepath)  # no exception
