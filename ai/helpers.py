from django.conf import settings

from ai.config import TRIM_LONG_CONTENT_TO_LEN
from posts.helpers import MARKDOWN_IMAGES_RE


def post_ai_context(post, *, text_limit=None, include_moderation=False):
    author = post.author
    is_author_public = not author.deleted_at and author.profile_publicity_level != author.PUBLICITY_LEVEL_PRIVATE
    source = post.metadata or {}
    metadata = {
        key: source[key]
        for key in ("url", "domain", "title", "favicon", "summary", "image", "description")
        if key in source
    }
    event = source.get("event") or {}

    if event:
        metadata["event"] = {
            key: event[key]
            for key in ("day", "month", "year", "time", "timezone", "utc_offset", "location")
            if key in event
        }

    battle = source.get("battle") or {}

    if battle:
        metadata["battle"] = {
            "sides": {
                key: {"name": value.get("name")}
                for key, value in battle.get("sides", {}).items()
            },
        }

    moderation = post.moderation_data or {}
    context = {
        "id": str(post.id),
        "post_url": f"{settings.APP_HOST}{post.get_absolute_url()}",
        "slug": post.slug,
        "type": post.type,
        "title": post.title,
        "author": {
            "slug": post.author.slug,
            "full_name": post.author.full_name,
            "profile_url": f"{settings.APP_HOST}{post.author.get_absolute_url()}",
        } if is_author_public else None,
        "text_markdown": post.text[:text_limit] if text_limit is not None else post.text,
        "text_truncated": text_limit is not None and len(post.text) > text_limit,
        "image": post.image,
        "markdown_images": MARKDOWN_IMAGES_RE.findall(post.text),
        "url": post.url,
        "metadata": metadata,
        "room": post.room.title if post.room else None,
        "label_code": post.label_code,
        "collectible_tag_code": post.collectible_tag_code,
        "comment_template": post.comment_template,
        "visibility": post.visibility,
        "is_public": post.is_public,
        "is_room_only": post.is_room_only,
        "is_commentable": post.is_commentable,
        "upvotes": post.upvotes,
        "comment_count": post.comment_count,
        "view_count": post.view_count,
        "hotness": post.hotness,
        "moderation_status": post.moderation_status,
        **{
            f"{field}_utc": getattr(post, field).isoformat() if getattr(post, field) else None
            for field in (
                "created_at", "published_at", "updated_at", "last_activity_at", "deleted_at", "is_pinned_until",
            )
        },
    }

    if include_moderation:
        context["moderation"] = {
            key: moderation[key] for key in ("reason", "text", "moderated_at") if key in moderation
        }

    return context


def user_ai_context(user, *, include_profile=False):
    if not user or user.deleted_at or user.profile_publicity_level == user.PUBLICITY_LEVEL_PRIVATE:
        return None

    return {
        "slug": user.slug,
        "full_name": user.full_name,
        "profile_url": f"{settings.APP_HOST}{user.get_absolute_url()}",
        **({
            field: (getattr(user, field) or "")[:2000]
            for field in ("bio", "company", "position", "city", "country")
        } if include_profile else {}),
    }


def comment_ai_context(comment):
    parent = comment.reply_to
    return {
        "id": str(comment.id),
        "comment_url": f"{settings.APP_HOST}{comment.get_absolute_url()}",
        "title": comment.title,
        "text_markdown": comment.text[:TRIM_LONG_CONTENT_TO_LEN],
        "text_truncated": len(comment.text) > TRIM_LONG_CONTENT_TO_LEN,
        "url": comment.url,
        "markdown_images": MARKDOWN_IMAGES_RE.findall(comment.text),
        "author": user_ai_context(comment.author),
        "upvotes": comment.upvotes,
        "created_at_utc": comment.created_at.isoformat() if comment.created_at else None,
        "updated_at_utc": comment.updated_at.isoformat() if comment.updated_at else None,
        "post": post_ai_context(comment.post, text_limit=TRIM_LONG_CONTENT_TO_LEN),
        "reply_to": {
            "id": str(parent.id),
            "text_markdown": parent.text[:TRIM_LONG_CONTENT_TO_LEN],
        } if parent and parent.is_visible and not parent.is_deleted else None,
        "battle_side": (comment.metadata or {}).get("battle", {}).get("side"),
    }
