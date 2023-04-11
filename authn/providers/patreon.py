import logging
from datetime import datetime, timedelta
from json import JSONDecodeError
from typing import Optional

import requests
from django.conf import settings

from authn.exceptions import PatreonException
from authn.providers.common import Membership, Platform
from utils.date import first_day_of_next_month

log = logging.getLogger(__name__)


def fetch_auth_data(code: str) -> dict:
    try:
        response = requests.post(
            url=settings.PATREON_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": settings.PATREON_CLIENT_ID,
                "client_secret": settings.PATREON_CLIENT_SECRET,
                "redirect_uri": settings.PATREON_REDIRECT_URL,
            },
        )
    except requests.exceptions.RequestException as ex:
        raise PatreonException(ex)

    if response.status_code >= 400:
        log.warning(f"Patreon error on login {response.status_code}: {response.text}")
        raise PatreonException(response.text)

    try:
        return response.json()
    except JSONDecodeError:
        raise PatreonException("Patreon is down. Please try again")


def refresh_auth_data(refresh_token: str) -> dict:
    try:
        response = requests.post(
            url=settings.PATREON_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
                "client_id": settings.PATREON_CLIENT_ID,
                "client_secret": settings.PATREON_CLIENT_SECRET,
            },
        )
    except requests.exceptions.RequestException as ex:
        log.warning(f"Patreon error on refreshing token: {ex}")
        raise PatreonException(ex)

    if response.status_code >= 400:
        log.warning(f"Patreon error on refreshing token {response.status_code}: {response.text}")
        raise PatreonException(response.text)

    try:
        return response.json()
    except JSONDecodeError:
        raise PatreonException("Patreon is down. Please try again")


def fetch_user_data(access_token: str) -> dict:
    try:
        response = requests.get(
            url=settings.PATREON_USER_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Bearer {access_token}",
            },
            params={
                "include": "memberships",
                "fields[user]": "full_name,email,image_url,about",
                "fields[member]": "patron_status,last_charge_status,last_charge_date,pledge_relationship_start,"
                                  "lifetime_support_cents,currently_entitled_amount_cents",
            },
        )
    except requests.exceptions.RequestException as ex:
        log.exception(f"Patreon error on fetching user data: {ex}")
        raise PatreonException(ex)

    if response.status_code >= 400:  # unauthorized etc
        log.warning(
            f"Patreon error on fetching user data {response.status_code}: {response.text}"
        )
        raise PatreonException(response.text)

    try:
        return response.json()
    except JSONDecodeError:
        raise PatreonException("Patreon is down. Please try again")


def parse_active_membership(user_data: dict) -> Optional[Membership]:
    log.info(f"Parse membership: {user_data}")

    if not user_data or not user_data.get("data") or not user_data.get("included"):
        return None

    for membership in user_data["included"]:
        if membership["attributes"]["patron_status"] == "active_patron" \
                and membership["attributes"]["last_charge_status"] == "Paid":

            now = datetime.utcnow()

            membership_started_at = datetime.strptime(
                str(membership["attributes"]["pledge_relationship_start"])[:10], "%Y-%m-%d"
            ) if membership["attributes"]["pledge_relationship_start"] else now

            last_charged_at = None
            if membership["attributes"]["last_charge_date"]:
                last_charged_at = datetime.strptime(
                    str(membership["attributes"]["last_charge_date"])[:10], "%Y-%m-%d"
                )

            if last_charged_at:
                membership_expires_at = last_charged_at + timedelta(days=45)
            else:
                membership_expires_at = first_day_of_next_month(now) + timedelta(days=7)

            return Membership(
                platform=Platform.patreon,
                user_id=user_data["data"]["id"],
                full_name=user_data["data"]["attributes"]["full_name"],
                email=user_data["data"]["attributes"]["email"],
                image=None,  # user_data["data"]["attributes"]["image_url"],
                started_at=membership_started_at,
                charged_at=last_charged_at,
                expires_at=membership_expires_at,
                lifetime_support_cents=int(membership["attributes"]["lifetime_support_cents"] or 0),
                currently_entitled_amount_cents=int(membership["attributes"]["currently_entitled_amount_cents"] or 0),
            )

    return None
