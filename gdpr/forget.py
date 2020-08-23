from auth.models import Session, Code
from bookmarks.models import PostBookmark
from posts.models import Post
from users.models.achievements import UserAchievement
from users.models.expertise import UserExpertise
from users.models.tags import UserTag
from users.models.user import User
from utils.strings import random_string


def delete_user_data(user: User):
    if user.deleted_at is None:
        # user changed his mind
        return

    # anonymize user
    user.slug = random_string(length=32)
    user.email = f"{user.slug}@deleted.com"
    user.is_email_unsubscribed = True
    user.is_email_verified = False
    user.moderation_status = User.MODERATION_STATUS_REJECTED
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

    # delete draft posts
    Post.objects.filter(author=user, is_visible=False).delete()

    # drop related data
    UserAchievement.objects.filter(user=user).delete()
    UserTag.objects.filter(user=user).delete()
    UserExpertise.objects.filter(user=user).delete()
    Session.objects.filter(user=user).delete()
    Code.objects.filter(user=user).delete()
    PostBookmark.objects.filter(user=user).delete()
