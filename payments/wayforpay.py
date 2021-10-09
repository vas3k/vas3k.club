# https://wiki.wayforpay.com/ru/view/608996852

import hashlib
import hmac
import logging
import time
from datetime import date, timedelta
from enum import Enum
from uuid import uuid4

import requests
from dataclasses import dataclass
from django.conf import settings

from payments.products import club_subscription_activator

log = logging.getLogger()

WAYFORPAY_PRODUCTS = {
    "club1": {
        "code": "club1",
        "description": "Месяц членства в Клубе",
        "amount": 1,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=31),
        },
    },
    "club12": {
        "code": "club12",
        "description": "Год членства в Клубе",
        "amount": 10,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365),
        },
    },
    "club1_recurrent": {
        "code": "club1",
        "description": "Месяц членства в Клубе",
        "amount": 1,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=31),
        },
        "regular": "monthly",
    },
    "club12_recurrent": {
        "code": "club12",
        "description": "Год членства в Клубе",
        "amount": 10,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365),
        },
        "regular": "yearly",
    },
}


class TransactionStatus(Enum):
    PENDING = "Pending"
    REFUNDED = "Refunded"
    APPROVED = "Approved"


@dataclass
class Invoice:
    id: str
    url: str


class WayForPayService:
    @classmethod
    def create_payment(cls, product_code: str) -> Invoice:
        product_data = WAYFORPAY_PRODUCTS[product_code]

        order_id = uuid4().hex

        log.info("Try to create payment %s %s", product_code, order_id)

        payload = {
            "merchantAccount": "4aff_club",
            "merchantDomainName": "4aff.club",
            "serviceUrl": "https://4aff.club/monies/wayforpay/webhook/",
            "orderReference": order_id,
            "orderDate": int(time.time()),
            "amount": product_data["amount"],
            "currency": "USD",
            "productName": [product_data["description"]],
            "productPrice": [product_data["amount"]],
            "productCount": [1],
        }

        if "regular" in product_data:
            payload.update({
                "regularMode": product_data["regular"],
                "regularOn": 1,
                "dateNext": (date.today() + product_data["data"]["timedelta"]).strftime("%d.%m.%Y"),
                "dateEnd": "01.01.2100",
            })
        else:
            payload.update({
                "regularMode": "client",
            })

        fields = (
            "merchantAccount", "merchantDomainName", "orderReference", "orderDate", "amount", "currency",
            "productName", "productCount", "productPrice",
        )

        string = ";".join([
            str(payload[field][0] if isinstance(payload[field], list) else payload[field])
            for field in fields
        ])
        signature = hmac.new(settings.WAYFORPAY_SECRET.encode("utf-8"), string.encode("utf-8"), hashlib.md5).hexdigest()
        payload["merchantSignature"] = signature

        response = requests.post("https://secure.wayforpay.com/pay?behavior=offline", json=payload)
        log.info("Payment answer %s %s", response.status_code, response.text)

        response.raise_for_status()

        invoice = Invoice(
            id=order_id,
            url=response.json()["url"],
        )
        return invoice

    @classmethod
    def create_invoice(cls, product_code: str) -> Invoice:
        invoice_id = uuid4().hex

        log.info("Try to create invoice %s", product_code)

        payload = {
            "transactionType": "CREATE_INVOICE",
            "merchantAccount": "4aff_club",
            "merchantDomainName": "4aff.club",
            "apiVersion": 1,
            "serviceUrl": "https://4aff.club/monies/wayforpay/webhook/",
            "orderReference": invoice_id,
            "orderDate": int(time.time()),
            "amount": 1,
            "currency": "USD",
            "orderTimeout": 24 * 60 * 60,
            "productName": [WAYFORPAY_PRODUCTS[product_code]["description"]],
            "productPrice": [WAYFORPAY_PRODUCTS[product_code]["amount"]],
            "productCount": [1],
        }

        fields = (
            "merchantAccount", "merchantDomainName", "orderReference", "orderDate", "amount", "currency",
            "productName", "productCount", "productPrice",
        )

        string = ";".join([
            str(payload[field][0] if isinstance(payload[field], list) else payload[field])
            for field in fields
        ])
        signature = hmac.new(settings.WAYFORPAY_SECRET.encode("utf-8"), string.encode("utf-8"), hashlib.md5).hexdigest()
        payload["merchantSignature"] = signature

        response = requests.post("https://api.wayforpay.com/api", json=payload)
        log.info("Invoice answer %s %s", response.status_code, response.text)

        response.raise_for_status()

        invoice = Invoice(
            id=invoice_id,
            url=response.json()["invoiceUrl"],
        )
        return invoice

    @classmethod
    def accept_invoice(cls, payload: dict) -> [TransactionStatus, dict]:
        log.info("Accept invoice %r", payload)

        now = int(time.time())

        string = f"{payload['orderReference']};accept;{now}"
        signature = hmac.new(settings.WAYFORPAY_SECRET.encode("utf-8"), string.encode("utf-8"), hashlib.md5).hexdigest()

        status = {
            TransactionStatus.APPROVED.value: TransactionStatus.APPROVED,
            TransactionStatus.REFUNDED.value: TransactionStatus.REFUNDED,
        }.get(payload['transactionStatus'], TransactionStatus.PENDING)

        log.info("Status %s", status)

        return status, {
            "orderReference": payload["orderReference"],
            "status": "accept",
            "time": now,
            "signature": signature,
        }
