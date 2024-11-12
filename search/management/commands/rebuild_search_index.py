import logging

from django.core.management import BaseCommand
from django.db import OperationalError

from comments.models import Comment
from posts.models.post import Post
from search.models import SearchIndex
from users.models.user import User
from utils.queryset import chunked_queryset

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Rebuild search index for posts and users"

    def handle(self, *args, **options):
        SearchIndex.objects.all().delete()
        indexed_comment_count = 0
        indexed_post_count = 0
        indexed_user_count = 0

        for chunk in chunked_queryset(
            Comment.visible_objects().filter(is_deleted=False, post__is_visible=True)
        ):
            for comment in chunk:
                self.stdout.write(f"Indexing comment: {comment.id}")

                try:
                    SearchIndex.update_comment_index(comment)
                except OperationalError as ex:
                    log.exception("Failed to update comment index", exc_info=ex)
                    continue

                indexed_comment_count += 1

        for chunk in chunked_queryset(
            Post.visible_objects().filter(is_shadow_banned=False)
        ):
            for post in chunk:
                self.stdout.write(f"Indexing post: {post.slug}")

                try:
                    SearchIndex.update_post_index(post)
                except OperationalError as ex:
                    log.exception("Failed to update post index", exc_info=ex)
                    continue

                indexed_post_count += 1

        for chunk in chunked_queryset(
            User.objects.filter(moderation_status=User.MODERATION_STATUS_APPROVED)
        ):
            for user in chunk:
                self.stdout.write(f"Indexing user: {user.slug}")

                try:
                    SearchIndex.update_user_index(user)
                except OperationalError as ex:
                    log.exception("Failed to update user index", exc_info=ex)
                    continue

                try:
                    SearchIndex.update_user_tags(user)
                except OperationalError as ex:
                    log.exception("Failed to update user tags", exc_info=ex)
                    continue

                indexed_user_count += 1

        self.stdout.write(
            f"Done 🥙 "
            f"Comments: {indexed_comment_count} Posts: {indexed_post_count} Users: {indexed_user_count}"
        )
