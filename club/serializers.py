from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from django.core.paginator import Page
from django.db.models import QuerySet, Model
from django.forms import BaseForm
from django.template.context import BaseContext

SKIP_KEYS = {"csrf_token", "request", "perms", "messages", "view", "DEFAULT_PAGE_SIZE"}

SENSITIVE_KEYS = {
    "muted_user_ids",
    "user_notes",
    "moderator_notes",
    "note",
    "muted",
    "subscription",
}


def serialize(value):
    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, str):
        return value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    if isinstance(value, Page):
        return {
            "items": [serialize(item) for item in value],
            "page": value.number,
            "total_pages": value.paginator.num_pages,
            "count": value.paginator.count,
            "has_next": value.has_next(),
            "has_previous": value.has_previous(),
        }

    if isinstance(value, Model):
        if hasattr(value, "to_dict"):
            return value.to_dict()
        return str(value)

    if isinstance(value, QuerySet):
        return [serialize(item) for item in value]

    if isinstance(value, BaseForm):
        return None

    if isinstance(value, BaseContext):
        flat = {}
        for d in value.dicts:
            if isinstance(d, dict):
                flat.update(d)
        return serialize(flat)

    if isinstance(value, dict):
        return {
            k: serialize(v)
            for k, v in value.items()
            if k not in SKIP_KEYS and k not in SENSITIVE_KEYS and not k.startswith("_")
        }

    if isinstance(value, (list, tuple, set, frozenset)):
        return [serialize(item) for item in value]

    if hasattr(value, "to_dict"):
        return value.to_dict()

    try:
        return str(value)
    except Exception:
        return None
