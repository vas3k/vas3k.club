from django.core.management import BaseCommand

from comments.models import Comment
from posts.models.post import Post
from search.models import SearchIndex
from users.models.user import User
from utils.queryset import chunked_queryset


class Command(BaseCommand):
    help = "Refresh search entries in place and remove entries no longer eligible for indexing"

    def handle(self, *args, **options):
        comments = (
            Comment.visible_objects()
            .filter(is_deleted=False)
            .exclude(post__visibility=Post.VISIBILITY_DRAFT)
        )
        posts = Post.objects.exclude(visibility=Post.VISIBILITY_DRAFT)
        users = User.objects.filter(moderation_status=User.MODERATION_STATUS_APPROVED)

        indexed_comment_count = 0
        indexed_post_count = 0
        indexed_user_count = 0

        # Keep existing entries searchable while refreshing them. Let database errors
        # abort the command so an interrupted run can be rerun without emptying the index.
        for chunk in chunked_queryset(comments.select_related("author", "post")):
            for comment in chunk:
                self.stdout.write(f"Indexing comment: {comment.id}")
                SearchIndex.update_comment_index(comment)
                indexed_comment_count += 1

        for chunk in chunked_queryset(posts.select_related("author", "room")):
            for post in chunk:
                self.stdout.write(f"Indexing post: {post.slug}")
                SearchIndex.update_post_index(post)
                indexed_post_count += 1

        for chunk in chunked_queryset(users):
            for user in chunk:
                self.stdout.write(f"Indexing user: {user.slug}")
                SearchIndex.update_user_index(user)
                SearchIndex.update_user_tags(user)
                indexed_user_count += 1

        # Prune using current source eligibility, not whether an entry was touched
        # during this run. The subqueries also remove orphaned entries with null FKs.
        SearchIndex.objects.filter(type=SearchIndex.TYPE_COMMENT).exclude(
            comment_id__in=comments.order_by().values("pk"),
        ).delete()
        SearchIndex.objects.filter(type=SearchIndex.TYPE_POST).exclude(
            post_id__in=posts.order_by().values("pk"),
        ).delete()
        SearchIndex.objects.filter(type=SearchIndex.TYPE_USER).exclude(
            user_id__in=users.order_by().values("pk"),
        ).delete()

        self.stdout.write(
            f"Done 🥙 "
            f"Comments: {indexed_comment_count} Posts: {indexed_post_count} Users: {indexed_user_count}"
        )
