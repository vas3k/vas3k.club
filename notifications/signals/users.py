from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django_q.tasks import async_task

from bot.common import ADMIN_CHAT, send_telegram_message
from users.models.user import User

TRACK_DIFF_FIELDS = {
    "email",
    "full_name",
    "avatar",
    "company",
    "position",
    "city",
    "country",
    "bio",
    "email_digest_type",
}


@receiver(post_save, sender=User)
def create_or_update_user(sender, instance, created, **kwargs):
    async_task(async_create_or_update_user, instance, created)


def async_create_or_update_user(user, created):
    user_profile_url = settings.APP_HOST + reverse("profile", kwargs={"user_slug": user.slug})

    if created:
        # new user registered
        send_telegram_message(
            chat=ADMIN_CHAT,
            text=f"👶 <b>Зарегался новенький:</b> <a href=\"{user_profile_url}\">{user.slug}</a>"
        )
