from datetime import datetime

import stripe
import logging
from typing import List, Optional

from django.core.management import BaseCommand
from django.conf import settings
from django.template.loader import render_to_string

from notifications.email.sender import send_transactional_email

stripe.api_key = settings.STRIPE_API_KEY


BATCH_SIZE = 100
MAX_LIMIT = 1000


class Command(BaseCommand):
    help = "Update Stripe subscription prices"

    def add_arguments(self, parser):
        parser.add_argument("--old-price-id", type=str, required=True)
        parser.add_argument("--new-price-id", type=str, required=True)
        parser.add_argument("--limit", type=int, required=False)

    def handle(self, *args, **options):
        # Configuration
        old_price_id = options.get("old_price_id")
        new_price_id = options.get("new_price_id")
        global_limit = options.get("limit") or MAX_LIMIT

        # Get prices
        old_stripe_price = stripe.Price.retrieve(old_price_id)
        new_stripe_price = stripe.Price.retrieve(new_price_id)

        self.stdout.write(f"Price update from {old_stripe_price.unit_amount // 100} "
                          f"to {new_stripe_price.unit_amount // 100}")

        # Fetch existing subscriptions
        subscriptions = fetch_subscriptions(old_price_id, limit=global_limit)
        self.stdout.write(f"Found {len(subscriptions)} subscriptions to update")

        # For stats
        success_count = 0
        failure_count = 0

        for subscription in subscriptions:
            customer_email = subscription.customer.email
            current_period_end = datetime.fromtimestamp(subscription.current_period_end)

            self.stdout.write(f"Customer: {customer_email}, ID {subscription.id} "
                              f"Subscription: {subscription['items']['data']}")

            result = update_subscription_price(
                subscription,
                old_price_id,
                new_price_id,
            )

            if result:
                self.stdout.write(f"Sending email to {customer_email}, period ends {current_period_end}...")

                email = render_to_string("emails/price_increase.html", {
                    "old_price": old_stripe_price.unit_amount // 100,
                    "new_price": new_stripe_price.unit_amount // 100,
                    "current_period_end": current_period_end,
                })

                send_transactional_email(
                    recipient=customer_email,
                    subject=f"🥲 Долор уже не тот, что раньше",
                    html=email,
                )

                success_count += 1
            else:
                failure_count += 1

            self.stdout.write(f"Next one...")

        self.stdout.write(f"""
        Price update completed:
        - Total subscriptions processed: {len(subscriptions)}
        - Successful updates: {success_count}
        - Failed updates: {failure_count}
        """)


def fetch_subscriptions(old_price_id: str, limit: int = MAX_LIMIT) -> List[stripe.Subscription]:
    subscriptions = []
    has_more = True
    starting_after = None

    while has_more and len(subscriptions) < limit:
        try:
            result = stripe.Subscription.list(
                limit=BATCH_SIZE,
                price=old_price_id,
                status="active",
                starting_after=starting_after,
                expand=['data.customer']
            )

            subscriptions.extend(result.data)

            has_more = result.has_more

            if has_more and result.data:
                starting_after = result.data[-1].id

        except stripe.error.StripeError as e:
            logging.error(f"Error fetching subscriptions: {str(e)}")
            raise

    return subscriptions[:limit]


def update_subscription_price(
    subscription: stripe.Subscription,
    old_price_id: str,
    new_price_id: str,
) -> Optional[stripe.Subscription]:
    try:
        # Find the subscription item with the old price
        sub_item = next(
            (item for item in subscription["items"]["data"] if item["price"].id == old_price_id),
            None
        )

        if not sub_item:
            logging.warning(f"Subscription {subscription.id} doesn't have the old price ID")
            return None

        # Update the subscription
        updated_subscription = stripe.Subscription.modify(
            subscription.id,
            automatic_tax={"enabled": True},
            proration_behavior="none",  # apply only from the next billing cycle
            items=[{
                'id': sub_item.id,
                'price': new_price_id,
            }]
        )

        logging.info(
            f"Successfully updated subscription {subscription.id} "
            f"for customer {subscription.customer.email}"
        )

        logging.info(f"Subscription {subscription.id} with sub_item {sub_item.id} "
                     f"is updated to new price {new_price_id}")
        return updated_subscription

    except stripe.error.StripeError as e:
        logging.error(
            f"Error updating subscription {subscription.id} "
            f"for customer {subscription.customer.email}: {str(e)}"
        )
        return None
