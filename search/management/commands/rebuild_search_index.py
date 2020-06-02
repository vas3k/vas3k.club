import logging

from django.core.management import BaseCommand

from comments.models import Comment
from posts.models import Post
from search.models import SearchIndex
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Rebuild search index for posts and users"

    def handle(self, *args, **options):
        SearchIndex.objects.all().delete()

        for comment in Comment.visible_objects().filter(is_deleted=False, post__is_visible=True):
            self.stdout.write(f"Indexing comment: {comment.id}")
            SearchIndex.update_comment_index(comment)

        for post in Post.visible_objects().filter(is_shadow_banned=False):
            self.stdout.write(f"Indexing post: {post.slug}")
            SearchIndex.update_post_index(post)

        for user in User.objects.filter(moderation_status=User.MODERATION_STATUS_APPROVED):
            self.stdout.write(f"Indexing user: {user.slug}")
            SearchIndex.update_user_index(user)
            SearchIndex.update_user_tags(user)

        self.stdout.write("Done 🥙")
