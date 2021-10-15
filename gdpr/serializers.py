from typing import List

from django.conf import settings
from django.urls import reverse

from bookmarks.models import PostBookmark
from comments.models import Comment
from posts.models.post import Post
from posts.models.votes import PostVote
from users.models.expertise import UserExpertise
from users.models.tags import UserTag
from users.models.user import User


def post_to_md(post: Post) -> str:
    return f"# {post.title}\n\n{post.text}"


def post_to_json(post: Post) -> dict:
    return {
        "id": str(post.id),
        "slug": post.slug,
        "author_id": str(post.author_id),
        "type": post.type,
        "topic": post.topic.name if post.topic else None,
        "label": post.label,
        "title": post.title,
        "text": post.text,
        "url": post.url,
        "image": post.image,
        "metadata": post.metadata,
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat(),
        "last_activity_at": post.last_activity_at.isoformat(),
        "comment_count": post.comment_count,
        "view_count": post.view_count,
        "upvotes": post.upvotes,
    }


def comment_to_md(comment: Comment) -> str:
    return f"{comment.text}\n\n- {comment.author.slug}"


def comments_to_json(comments: List[Comment]) -> dict:
    return {
        "comments": [
            comment_to_json(comment) for comment in comments
        ]
    }


def comment_to_json(comment: Comment) -> dict:
    return {
        "id": str(comment.id),
        "author_id": str(comment.author_id),
        "post_id": str(comment.post_id),
        "post_title": comment.post.title,
        "reply_to_id": str(comment.reply_to_id) if comment.reply_to else None,
        "title": comment.title,
        "text": comment.text,
        "url": comment.url,
        "metadata": comment.metadata,
        "created_at": comment.created_at.isoformat(),
        "updated_at": comment.updated_at.isoformat(),
        "upvotes": comment.upvotes,
        "is_visible": comment.is_visible,
        "is_deleted": comment.is_deleted,
        "is_pinned": comment.is_pinned,
    }


def user_to_json(user: User) -> dict:
    return {
        "id": str(user.id),
        "slug": user.slug,
        "email": user.email,
        "full_name": user.full_name,
        "avatar": user.avatar,
        "company": user.company,
        "position": user.position,
        "city": user.city,
        "country": user.country,
        "bio": user.bio,
        "contact": user.contact,
        "hat": user.hat,
        "balance": user.balance,
        "upvotes": user.upvotes,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_activity_at": user.last_activity_at.isoformat() if user.last_activity_at else None,
        "membership_started_at": user.membership_started_at.isoformat() if user.membership_started_at else None,
        "membership_expires_at": user.membership_expires_at.isoformat() if user.membership_expires_at else None,
        "membership_platform_type": user.membership_platform_type,
        "patreon_id": user.patreon_id,
        "email_digest_type": user.email_digest_type,
        "telegram_id": user.telegram_id,
        "telegram_data": user.telegram_data,
        "stripe_id": user.stripe_id,
        "is_email_verified": user.is_email_verified,
        "is_email_unsubscribed": user.is_email_unsubscribed,
        "moderation_status": user.moderation_status,
        "roles": user.roles,
    }


def user_tags_to_json(user_tags: List[UserTag]) -> dict:
    return {
        "user_tags": [
            user_tag_to_json(user_tag) for user_tag in user_tags
        ]
    }


def user_tag_to_json(user_tag: UserTag) -> dict:
    return {
        "user_id": str(user_tag.user_id),
        "name": user_tag.name,
        "created_at": user_tag.created_at.isoformat() if user_tag.created_at else None,
    }


def user_expertises_to_json(user_expertises: List[UserExpertise]) -> dict:
    return {
        "user_expertise": [
            user_expertise_to_json(user_expertise) for user_expertise in user_expertises
        ]
    }


def user_expertise_to_json(user_expertise: UserExpertise) -> dict:
    return {
        "user_id": str(user_expertise.user_id),
        "name": user_expertise.name,
        "value": user_expertise.value,
        "created_at": user_expertise.created_at.isoformat() if user_expertise.created_at else None,
    }


def bookmarks_to_json(bookmarks: List[PostBookmark]) -> dict:
    return {
        "bookmarks": [
            bookmark_to_json(bookmark) for bookmark in bookmarks
        ]
    }


def bookmark_to_json(bookmark: PostBookmark) -> dict:
    return {
        "url": settings.APP_HOST + reverse("show_post", kwargs={
            "post_type": bookmark.post.type, "post_slug": bookmark.post.slug
        }),
        "created_at": bookmark.created_at.isoformat() if bookmark.created_at else None,
    }


def upvotes_to_json(upvotes: List[PostVote]) -> dict:
    return {
        "upvotes": [
            upvote_to_json(upvote) for upvote in upvotes
        ]
    }


def upvote_to_json(upvote: PostVote) -> dict:
    return {
        "url": settings.APP_HOST + reverse("show_post", kwargs={
            "post_type": upvote.post.type, "post_slug": upvote.post.slug
        }),
        "created_at": upvote.created_at.isoformat() if upvote.created_at else None,
        "title": upvote.post.title,
    }
