import logging

from django.core.management import BaseCommand

from common.data.tags import HOBBIES, PERSONAL, TECH, CLUB
from tags.models import Tag

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reads tags from data files and upserts them into the database"

    def handle(self, *args, **options):
        update_tag_group(Tag.GROUP_HOBBIES, HOBBIES)
        self.stdout.write(f"{len(HOBBIES)} hobbies")

        update_tag_group(Tag.GROUP_PERSONAL, PERSONAL)
        self.stdout.write(f"{len(PERSONAL)} personal")

        update_tag_group(Tag.GROUP_TECH, TECH)
        self.stdout.write(f"{len(TECH)} tech")

        update_tag_group(Tag.GROUP_CLUB, CLUB)
        self.stdout.write(f"{len(CLUB)} club")

        all_tag_keys = list(dict(HOBBIES).keys()) \
            + list(dict(PERSONAL).keys()) \
            + list(dict(TECH).keys()) \
            + list(dict(CLUB).keys())
        Tag.objects\
            .filter(group__in=[Tag.GROUP_HOBBIES, Tag.GROUP_PERSONAL, Tag.GROUP_TECH, Tag.GROUP_CLUB])\
            .exclude(code__in=all_tag_keys)\
            .delete()

        self.stdout.write("Done 🥙")


def update_tag_group(group, tag_list):
    for index, (tag_code, tag_name) in enumerate(tag_list):
        Tag.objects.update_or_create(
            code=tag_code,
            defaults=dict(
                group=group,
                name=tag_name,
                index=index,
            )
        )
