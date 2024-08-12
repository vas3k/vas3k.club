import logging
import os

from django.http import HttpResponse
from django.template import loader
from django_q.tasks import async_task

from club.exceptions import BadRequest
from notifications.email.sender import send_transactional_email
from notifications.signals.achievements import async_create_or_update_achievement

from payments.helpers import parse_stripe_webhook_event
from users.models.achievements import Achievement, UserAchievement
from users.models.user import User

log = logging.getLogger()

STRIPE_CAMP_WEBHOOK_SECRET = os.getenv("STRIPE_CAMP_WEBHOOK_SECRET")


# TODO: this is a temporary webhook, remove it after June 2024 (when the camp is over)
def stripe_camp_webhook(request):
    try:
        event = parse_stripe_webhook_event(request, STRIPE_CAMP_WEBHOOK_SECRET)
    except BadRequest as ex:
        return HttpResponse(ex.message, status=ex.code)

    if event["type"] == "checkout.session.completed":
    #     session = event["data"]["object"]
    #
    #     user = User.objects.filter(email=session["customer_details"]["email"].lower()).first()
    #
    #     # the user with the specified e-mail address does not necessarily exist
    #     if user:
    #         camp_achievement = Achievement.objects.filter(code="vas3k_camp_2024").first()
    #         UserAchievement.objects.get_or_create(
    #             user=user,
    #             achievement=camp_achievement,
    #         )
    #
    #     # send confirmation email
    #     camp_confirmation_template = loader.get_template("emails/camp_confirmation.html")
    #     async_task(
    #         send_transactional_email,
    #         recipient=session["customer_details"]["email"].lower(),
    #         subject=f"🔥 Ждём вас на Вастрик Кэмпе 2024",
    #         html=camp_confirmation_template.render({"user": user})
    #     )

        return HttpResponse("[ok]", status=200)

    return HttpResponse("[unknown event]", status=400)
