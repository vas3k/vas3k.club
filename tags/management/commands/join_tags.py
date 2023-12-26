import logging

from django.core.management import BaseCommand

from posts.models.post import Post
from tags.models import Tag, UserTag

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Join two tags into the first one (migrating all posts and users)"

    def add_arguments(self, parser):
        parser.add_argument("--first", type=str, required=True)
        parser.add_argument("--second", type=str, required=True)

    def handle(self, *args, **options):
        first_tag_code = options["first"]
        second_tag_code = options["second"]

        first_tag = Tag.objects.filter(code=first_tag_code).first()
        if not first_tag:
            self.stdout.write(f"Tag '{first_tag}' does not exist")
            return

        second_tag = Tag.objects.filter(code=second_tag_code).first()
        if not second_tag:
            self.stdout.write(f"Tag '{second_tag_code}' does not exist")
            return

        Post.objects.filter(collectible_tag_code=second_tag.code).update(collectible_tag_code=first_tag.code)
        for user_tag in UserTag.objects.filter(tag=second_tag):
            try:
                user_tag.tag = first_tag
                user_tag.save()
            except Exception as ex:
                self.stdout.write(f"UserTag '{user_tag.user_id}' is duplicate. Skipped. {ex}")

        Tag.objects.filter(code=second_tag.code).delete()

        self.stdout.write("Done 🥙")
