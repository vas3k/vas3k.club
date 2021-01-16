from django.core.management import BaseCommand

from comments.models import Comment
from posts.models.linked import LinkedPost
from posts.models.post import Post


class Command(BaseCommand):
    help = "Updates linked posts"

    def handle(self, *args, **options):
        LinkedPost.objects.all().delete()

        posts = Post.visible_objects().exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST])
        for post in posts:
            print(f"Parsing post: {post.slug}")
            LinkedPost.create_links_from_text(post, post.text)

        del posts

        comments = Comment.visible_objects()
        for comment in comments:
            print(f"Parsing comment: {comment.id}")
            LinkedPost.create_links_from_text(comment.post, comment.text)

        print("Done 🥙")
