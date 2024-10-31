# https://developers.cloudpayments.ru/api

import base64
import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import timedelta, datetime
from enum import Enum
from uuid import uuid4
from typing import List

import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth

from payments.products import club_subscription_activator
from users.models.user import User

log = logging.getLogger(__name__)

CLOUDPAYMENTS_PRODUCTS = {
    "club1_month": {
        "code": "club1_month",
        "description": "1 месяц членства в Клубе",
        "amount": 599,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=31),
        },
    },
    "club799_month": {
        "code": "club799_month",
        "description": "1 месяц членства в Клубе",
        "amount": 799,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=31),
        },
    },
    "club799_month_recurrent": {
        "code": "club799_month_recurrent",
        "description": "1 месяц членства в Клубе",
        "amount": 799,
        "recurrent": True,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=31),
        },
        "regular": "monthly",
    },
    # "club1_year": {
    #     "code": "club1_year",
    #     "description": "1 год членства в Клубе",
    #     "amount": 5999,
    #     "recurrent": False,
    #     "activator": club_subscription_activator,
    #     "data": {
    #         "timedelta": timedelta(days=365),
    #     },
    # },
    "club1_month_recurrent": {
        "code": "club1_month_recurrent",
        "description": "1 месяц членства в Клубе",
        "amount": 599,
        "recurrent": True,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=31),
        },
        "regular": "monthly",
    },
    # "club1_year_recurrent": {
    #     "code": "club1_year_recurrent",
    #     "description": "1 год членства в Клубе",
    #     "amount": 5999,
    #     "recurrent": False,
    #     "activator": club_subscription_activator,
    #     "data": {
    #         "timedelta": timedelta(days=365),
    #     },
    #     "regular": "yearly",
    # },
}


class TransactionStatus(Enum):
    PENDING = "Pending"
    REFUNDED = "Refunded"
    APPROVED = "Approved"
    UNKNOWN = "Unknown"


@dataclass
class Invoice:
    id: str
    url: str


class CloudPaymentsService:
    @classmethod
    def create_payment(cls, product_code: str, user: User) -> Invoice:
        product_data = CLOUDPAYMENTS_PRODUCTS[product_code]

        order_id = uuid4().hex

        log.info("Try to create payment %s %s", product_code, order_id)

        payload = {
            "Amount": product_data["amount"],
            "Currency": "RUB",
            "Description": product_data["description"],
            "RequireConfirmation": False,
            "InvoiceId": order_id,
            "SubscriptionBehavior": "CreateMonthly" if product_data.get("regular") == "monthly" else "",
            "SuccessRedirectUrl": "https://club.careerfactory.ru/auth/login/",
            "Email": user.email,
            "JsonData": {
                "CloudPayments": {
                    "CustomerReceipt": {
                        "Items": [
                            {
                                "label": product_data["description"],
                                "price": product_data["amount"],
                                "quantity": 1.00,
                                "amount": product_data["amount"],
                                "vat": 0,
                                "method": 0,
                                "object": 0,
                                "measurementUnit": "шт",
                            },
                        ],
                        "email": user.email,
                        "calculationPlace": "club.careerfactory.ru",
                        "amounts":
                            {
                                "electronic": product_data["amount"],
                                "advancePayment": 0,
                                "credit": 0,
                                "provision": 0
                            }
                    }
                }
            }
        }

        response = requests.post(
            "https://api.cloudpayments.ru/orders/create",
            auth=HTTPBasicAuth(settings.CLOUDPAYMENTS_API_ID, settings.CLOUDPAYMENTS_API_PASSWORD),
            json=payload,
        )

        log.info("Payment answer %s %s", response.status_code, response.text)

        response.raise_for_status()

        invoice = Invoice(
            id=order_id,
            url=response.json()["Model"]["Url"],
        )
        return invoice

    @classmethod
    def verify_webhook(cls, request) -> bool:
        log.info("Verify request")

        secret = bytes(settings.CLOUDPAYMENTS_API_PASSWORD, 'utf-8')

        signature = base64.b64encode(hmac.new(secret, request.body, digestmod=hashlib.sha256).digest())
        log.info('Signature %s against %s', signature, request.META.get('HTTP_CONTENT_HMAC'))

        return signature == bytes(request.META.get('HTTP_CONTENT_HMAC'), 'utf-8')

    @classmethod
    def accept_payment(cls, action: str, payload: dict) -> [TransactionStatus, dict]:
        log.info("Accept action %s, payment %r", action, payload)

        status = TransactionStatus.UNKNOWN

        if action == 'pay':
            status = TransactionStatus.APPROVED

        log.info("Status %s", status)

        return status, {"code": 0}

    @classmethod
    def get_subscriptions(cls, email: str) -> List[dict]:
        log.info("Try to get users's subscriptions %s", email)

        payload = {"accountId": email}

        response = requests.post(
            "https://api.cloudpayments.ru/subscriptions/find",
            auth=HTTPBasicAuth(settings.CLOUDPAYMENTS_API_ID, settings.CLOUDPAYMENTS_API_PASSWORD),
            json=payload,
        )

        log.info("Subscriptions answer %s %s", response.status_code, response.text)

        response.raise_for_status()

        data = response.json()["Model"]
        return [
            dict(
                id=row["Id"],
                next_charge_at=datetime.fromisoformat(row["NextTransactionDateIso"])
                if row["NextTransactionDateIso"] else None,
                amount=row["Amount"],
                interval=row["Interval"].lower(),
                status=row["Status"].lower(),
            )
            for row in data
        ]

    @classmethod
    def stop_subscription(cls, subscription_id: str) -> None:
        log.info("Try to stop subscription %s", subscription_id)

        payload = {"Id": subscription_id}

        response = requests.post(
            "https://api.cloudpayments.ru/subscriptions/cancel",
            auth=HTTPBasicAuth(settings.CLOUDPAYMENTS_API_ID, settings.CLOUDPAYMENTS_API_PASSWORD),
            json=payload,
        )

        log.info("Subscription stop answer %s %s", response.status_code, response.text)

        response.raise_for_status()
