from django.db.models.signals import post_save
from django.dispatch import receiver

from users.models.user import User


@receiver(post_save, sender=User)
def create_or_update_user(sender, instance, created, **kwargs):
    pass
