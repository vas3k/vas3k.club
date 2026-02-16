from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.core.paginator import Page
from django.db.models import Model, QuerySet
from django.forms import BaseForm
from django.template.context import BaseContext

SKIP_KEYS = {"csrf_token", "request", "perms", "messages", "view", "DEFAULT_PAGE_SIZE"}

# Context keys that contain sensitive data not safe for JSON API exposure.
# These are passed to templates for server-side rendering but should never
# be serialized into public JSON responses.
SENSITIVE_KEYS = {
    "muted_user_ids",  # list of UUIDs the user has muted (render_post)
    "user_notes",  # private notes about other users (render_post)
    "moderator_notes",  # moderator-only notes about a user (profile)
    "note",  # current user's private note about a profile (profile)
    "muted",  # whether current user muted this profile (profile)
    "subscription",  # current user's subscription object (render_post)
}


def serialize(value):
    """Recursively serialize a Django template context into JSON-safe structures."""
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

    # Django Page object (from paginator) → items + pagination meta
    if isinstance(value, Page):
        return {
            "items": [serialize(item) for item in value],
            "page": value.number,
            "total_pages": value.paginator.num_pages,
            "count": value.paginator.count,
            "has_next": value.has_next(),
            "has_previous": value.has_previous(),
        }

    # Model with to_dict() → use it
    if isinstance(value, Model):
        if hasattr(value, "to_dict"):
            return value.to_dict()
        return str(value)

    # QuerySet → evaluate and serialize each item
    if isinstance(value, QuerySet):
        return [serialize(item) for item in value]

    # Django forms → skip (not useful for JSON API)
    if isinstance(value, BaseForm):
        return None

    # BaseContext (Django template context wrapper) → flatten to dict
    if isinstance(value, BaseContext):
        flat = {}
        for d in value.dicts:
            if isinstance(d, dict):
                flat.update(d)
        return serialize(flat)

    # dict
    if isinstance(value, dict):
        return {
            k: serialize(v)
            for k, v in value.items()
            if k not in SKIP_KEYS and k not in SENSITIVE_KEYS and not k.startswith("_")
        }

    # list / tuple / set
    if isinstance(value, (list, tuple, set, frozenset)):
        return [serialize(item) for item in value]

    # anything with to_dict()
    if hasattr(value, "to_dict"):
        return value.to_dict()

    # last resort: try str()
    try:
        return str(value)
    except Exception:
        return None
