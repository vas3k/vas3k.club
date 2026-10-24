from importlib import import_module

from django.db import connection
from django.test import TestCase

from debug.utils_for_tests import create_approved_user
from posts.models.post import Post


class TestModerationDataMigration(TestCase):
    def setUp(self):
        self.author = create_approved_user("moderation_migration_author")
        self.post = Post.objects.create(author=self.author, title="Post", text="Content")
        self.migration = import_module("posts.migrations.0043_rename_moderation_data_user_to_moderator")

    def test_rename_preserves_metadata_and_existing_moderator(self):
        old_moderator = {"slug": "old-moderator", "avatar": "avatar.png", "full_name": "Old Moderator"}
        moderator = {"slug": "current-moderator"}
        metadata = {"message_id": 42, "reason": "title", "text": "Rejection", "moderated_at": "2026-01-01T12:00:00Z"}

        for before, expected in (
            (None, None),
            ({}, {}),
            ({"message_id": 42}, {"message_id": 42}),
            ({"user": old_moderator, **metadata}, {"moderator": old_moderator, **metadata}),
            ({"moderator": moderator, **metadata}, {"moderator": moderator, **metadata}),
            ({"user": old_moderator, "moderator": moderator, **metadata}, {"moderator": moderator, **metadata}),
        ):
            with self.subTest(before=before):
                self.post.moderation_data = before
                self.post.save(update_fields=["moderation_data"])

                with connection.cursor() as cursor:
                    cursor.execute(self.migration.Migration.operations[0].sql)

                self.post.refresh_from_db()
                self.assertEqual(self.post.moderation_data, expected)

    def test_rename_can_be_reversed_without_inventing_a_timestamp(self):
        original = {"user": {"slug": "moderator"}, "reason": "title", "message_id": 42}
        self.post.moderation_data = original
        self.post.save(update_fields=["moderation_data"])

        with connection.cursor() as cursor:
            cursor.execute(self.migration.Migration.operations[0].sql)
            cursor.execute(self.migration.Migration.operations[0].reverse_sql)

        self.post.refresh_from_db()
        self.assertEqual(self.post.moderation_data, original)
