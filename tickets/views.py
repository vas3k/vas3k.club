import logging
import os

import stripe
from django.http import HttpResponse
from django.template import loader
from django_q.tasks import async_task

from club.exceptions import BadRequest
from common.markdown.markdown import markdown_tg
from notifications.email.sender import send_transactional_email
from notifications.telegram.common import Chat, send_telegram_message

from payments.helpers import parse_stripe_webhook_event
from tickets.models import Ticket, TicketSale
from users.models.achievements import UserAchievement
from users.models.user import User

log = logging.getLogger()

STRIPE_TICKETS_WEBHOOK_SECRET = os.getenv("STRIPE_TICKETS_WEBHOOK_SECRET")
STRIPE_TICKETS_API_KEY = os.getenv("STRIPE_TICKETS_API_KEY")


def stripe_ticket_sale_webhook(request):
    try:
        event = parse_stripe_webhook_event(
            request=request,
            webhook_secret=STRIPE_TICKETS_WEBHOOK_SECRET,
            api_key=STRIPE_TICKETS_API_KEY
        )
    except BadRequest as ex:
        return HttpResponse(ex.message, status=ex.code)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session["id"]
        customer_email = session["customer_details"]["email"].lower()
        user = User.objects.filter(email=customer_email).first()
        ticket_codes_processed = set()

        try:
            session_with_items = stripe.checkout.Session.retrieve(
                session_id,
                expand=["line_items", "line_items.data.price.product"],
                api_key=STRIPE_TICKETS_API_KEY
            )

            # Process each item in the purchase
            if session_with_items.line_items:
                for item in session_with_items.line_items.data:
                    stripe_product_id = item.price.product.id

                    # Find the corresponding ticket
                    ticket, _ = Ticket.objects.get_or_create(
                        stripe_product_id=stripe_product_id,
                        defaults=dict(
                            code=stripe_product_id,
                            name=item.price.product.name,
                            limit_quantity=-1  # No limit by default
                        )
                    )
                    ticket_codes_processed.add(ticket.code)

                    # Create ticket sales (one for each quantity)
                    for _ in range(item.quantity):
                        TicketSale.objects.create(
                            user=user,
                            customer_email=customer_email,
                            stripe_payment_id=session.get("payment_intent"),
                            ticket=ticket,
                            metadata={
                                "price_paid": item.price.unit_amount / 100,  # Convert from cents
                                "currency": item.price.currency,
                                "purchased_at": session["created"],
                            },
                            session=session,
                        )

                    # Check if number of sales is exceeded
                    ticket_sales_count = TicketSale.objects.filter(ticket=ticket).count()
                    Ticket.objects.filter(stripe_product_id=stripe_product_id).update(
                        tickets_sold=ticket_sales_count
                    )
                    if ticket.limit_quantity >= 0 and ticket.stripe_payment_link_id:
                        if ticket_sales_count >= ticket.limit_quantity:
                            deactivate_payment_link(ticket.stripe_payment_link_id)

                    # Handle achievements
                    if user and ticket.achievement:
                        UserAchievement.objects.get_or_create(
                            user=user,
                            achievement=ticket.achievement,
                        )

            # Send confirmation emails (unique by ticket code)
            emails_to_send = Ticket.objects.filter(code__in=ticket_codes_processed)
            for ticket_email_template in emails_to_send:
                confirmation_template = loader.get_template("emails/custom_markdown.html")
                async_task(
                    send_transactional_email,
                    recipient=customer_email,
                    subject=ticket_email_template.send_email_title,
                    html=confirmation_template.render({
                        "user": user,
                        "title": ticket_email_template.send_email_title,
                        "body": ticket_email_template.send_email_markdown,
                    })
                )

                if user.telegram_id:
                    async_task(
                        send_telegram_message,
                        chat=Chat(id=user.telegram_id),
                        text=f"<b>{ticket_email_template.send_email_title}</b>\n\n"
                             f"{markdown_tg(ticket_email_template.send_email_markdown)}",
                    )

            return HttpResponse("[ok]", status=200)

        except stripe.error.StripeError as e:
            log.error(f"Stripe API error: {str(e)}")
            return HttpResponse(f"Stripe API error: {str(e)}", status=500)

    return HttpResponse("[unknown event]", status=400)


def deactivate_payment_link(payment_link_id):
    try:
        stripe.PaymentLink.modify(
            payment_link_id,
            active=False,
            api_key=STRIPE_TICKETS_API_KEY
        )
        log.info(f"Payment link {payment_link_id} has been deactivated due to sales limit")
        return True
    except stripe.error.StripeError as e:
        log.error(f"Failed to deactivate payment link {payment_link_id}: {str(e)}")
        return False
