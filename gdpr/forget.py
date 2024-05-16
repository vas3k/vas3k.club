from django.conf import settings
from django.db.models import Value
from django.db.models.functions import Replace

from authn.models.session import Session, Code
from bookmarks.models import PostBookmark
from comments.models import Comment
from posts.models.post import Post
from users.models.achievements import UserAchievement
from users.models.friends import Friend
from users.models.mute import Muted
from tags.models import UserTag
from users.models.user import User
from utils.strings import random_string


def delete_user_data(user: User):
    if user.deleted_at is None or user.moderation_status == User.MODERATION_STATUS_DELETED:
        # user changed his mind or already deleted
        return

    old_slug = str(user.slug)

    # anonymize user
    user.slug = random_string(length=16)
    user.email = f"{user.slug}@deleted.com"
    user.is_email_unsubscribed = True
    user.is_email_verified = False
    user.moderation_status = User.MODERATION_STATUS_DELETED
    user.full_name = "💀 Юзер Удалился"
    user.avatar = None
    user.company = None
    user.position = None
    user.city = None
    user.country = None
    user.geo = None
    user.bio = None
    user.contact = None
    user.email_digest_type = User.EMAIL_DIGEST_TYPE_NOPE
    user.telegram_id = None
    user.telegram_data = None
    user.membership_platform_data = None
    user.save()

    # delete intro
    Post.objects.filter(author=user, type=Post.TYPE_INTRO).delete()

    # delete draft and unpublished posts
    Post.objects.filter(author=user, is_visible=False).delete()

    # remove user from coauthors
    posts = Post.objects.filter(coauthors__contains=[old_slug])
    for post in posts:
        try:
            post.coauthors.remove(old_slug)
            post.save()
        except ValueError:
            pass

    # transfer visible post ownership to "@deleted" user
    deleted_user = User.objects.filter(slug=settings.DELETED_USERNAME).first()
    if deleted_user:
        Post.objects.filter(author=user, is_visible=True).update(author=deleted_user)

    # replace nickname in replies
    new_slug = str(user.slug)
    Comment.objects\
        .filter(reply_to__isnull=False, text__contains=f"@{old_slug}")\
        .update(
            text=Replace("text", Value(f"@{old_slug}"), Value(f"@{new_slug}")),
            html=None
        )

    # drop related data
    UserAchievement.objects.filter(user=user).delete()
    UserTag.objects.filter(user=user).delete()
    Session.objects.filter(user=user).delete()
    Code.objects.filter(user=user).delete()
    PostBookmark.objects.filter(user=user).delete()
    Friend.objects.filter(user_from=user).delete()
    Friend.objects.filter(user_to=user).delete()
    Muted.objects.filter(user_from=user).delete()
    Muted.objects.filter(user_to=user).delete()
