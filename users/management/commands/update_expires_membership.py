from datetime import datetime

from django.core.management import BaseCommand

from users.models.user import User

class Command(BaseCommand):
    help = "Updates all users membership to the end of 2030"

    def handle(self, *args, **options):
        users = User.objects.filter(moderation_status=User.MODERATION_STATUS_APPROVED)
        
        # Set membership_expires_at to December 31, 2030, 23:59:59
        end_of_2030 = datetime(2030, 12, 31, 23, 59, 59)
        
        updated_count = users.update(membership_expires_at=end_of_2030)
        
        self.stdout.write(f"Updated {updated_count} users' membership to the end of 2030 🥙")
