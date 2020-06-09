import logging

from django.core.management import BaseCommand

from common.data.achievements import ACHIEVEMENTS
from users.models.achievements import Achievement

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reads achievements from data files and upserts them into the database"

    def handle(self, *args, **options):
        for index, (code, data) in enumerate(ACHIEVEMENTS):
            Achievement.objects.update_or_create(
                code=code,
                defaults={**data, "index": index}
            )

        Achievement.objects.exclude(code__in=[code for code, _ in ACHIEVEMENTS]).delete()

        self.stdout.write("Done 🥙")
