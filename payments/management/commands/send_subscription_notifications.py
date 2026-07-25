import base64
import logging
from datetime import date, datetime, time, timedelta

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.management import BaseCommand

from common.messages import render_message_for_email, render_message_for_telegram
from notifications.email.sender import send_transactional_email
from notifications.telegram.common import Chat, send_telegram_message
from rooms.helpers import ban_user_in_all_chats, get_user_chats
from users.models.user import User

log = logging.getLogger(__name__)

STAGES = (
    {
        "name": "about_to_expire",
        "subject": "Ваша клубная карта скоро истечёт 😱",
        "template": "payments/subscription/about_to_expire.md",
        "expiration_day": lambda: date.today() + timedelta(days=14),
    },
    {
        "name": "expire",
        "subject": "Ваша подписка закончилась ☠️",
        "template": "payments/subscription/expired.md",
        "expiration_day": lambda: date.today(),
        "include_chats": True,
    },
    # {
    #     "name": "last_call",
    #     "subject": "Пока! из Клуба",
    #     "template": "payments/subscription/last_call.md",
    #     "expiration_day": lambda: date.today() - relativedelta(months=2) + timedelta(weeks=1),
    #     "include_chats": True,
    # },
    {
        "name": "final",
        "expiration_day": lambda: date.today() - relativedelta(months=2),
        "remove_from_chats": True,
    },
)


class Command(BaseCommand):
    help = "Send subscription lifecycle notifications and remove expired users from chats"

    def add_arguments(self, parser):
        parser.add_argument("--production", action="store_true")
        parser.add_argument(
            "--stage",
            choices=[stage["name"] for stage in STAGES],
            help="Run only one stage (default: all)",
        )

    def handle(self, *args, **options):
        production = options.get("production")
        selected = options.get("stage")
        stages = [stage for stage in STAGES if not selected or stage["name"] == selected]

        for stage in stages:
            self.stdout.write(f"=== {stage['name']} ===")
            self.send_stage(stage, production=production)

        self.stdout.write("Done 🥙")

    def send_stage(self, stage, production):
        if not production:
            users = User.objects.filter(
                email__in=settings.ADMINS,
                telegram_id__isnull=False,
            )
        else:
            day_start = datetime.combine(stage["expiration_day"](), time.min)
            users = User.objects.filter(
                membership_expires_at__gte=day_start,
                membership_expires_at__lt=day_start + timedelta(days=1),
                moderation_status=User.MODERATION_STATUS_APPROVED,
                deleted_at__isnull=True,
            ).exclude(membership_platform_type=User.MEMBERSHIP_PLATFORM_PATREON)

        for user in users:
            if user.membership_platform_data and user.membership_platform_data.get("recurrent"):
                self.stdout.write(f"User {user.email} has recurrent subscription, skipping...")
                continue

            if stage.get("remove_from_chats"):
                if production:
                    self.stdout.write(f"Removing {user.email} from Telegram chats...")
                    ban_user_in_all_chats(user, is_permanent=False)
                continue

            context = {
                "user": user,
                "settings": settings,
            }
            if stage.get("include_chats"):
                rooms = get_user_chats(user)
                if len(rooms) >= 3:
                    context["rooms"] = rooms

            if not user.is_email_unsubscribed:
                self.stdout.write(f"Sending email to {user.email}...")
                try:
                    secret_code = base64.b64encode(user.secret_hash.encode("utf-8")).decode()
                    email = render_message_for_email(
                        stage["template"],
                        title=stage["subject"],
                        context=context,
                    )
                    send_transactional_email(
                        recipient=user.email,
                        subject=stage["subject"],
                        html=email,
                        unsubscribe_link=f"{settings.APP_HOST}/notifications/unsubscribe/{user.id}/{secret_code}/",
                    )
                except Exception as ex:
                    self.stdout.write(f"Email to {user.email} failed: {ex}")
                    log.exception(f"Email to {user.email} failed: {ex}")

            if user.telegram_id:
                self.stdout.write(f"Sending telegram message to {user.email}...")
                try:
                    send_telegram_message(
                        chat=Chat(id=user.telegram_id),
                        text=render_message_for_telegram(stage["template"], context),
                    )
                except Exception as ex:
                    self.stdout.write(f"Telegram to {user.email} failed: {ex}")
