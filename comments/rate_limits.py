from datetime import datetime, timedelta

from django.conf import settings

from comments.models import Comment

def is_comment_rate_limit_exceeded(post, user):
    if user.is_moderator:
        return False

    # default limit is set in settings
    comments_per_day_limit = settings.RATE_LIMIT_COMMENTS_PER_DAY

    # post custom limits
    custom_rate_limit_for_post = post.get_custom_comment_limit()
    if custom_rate_limit_for_post is not None:
        comments_per_day_limit = custom_rate_limit_for_post

    # user custom limits
    custom_rate_limit_for_user = user.get_custom_comment_limit()
    if custom_rate_limit_for_user is not None:
        comments_per_day_limit = custom_rate_limit_for_user

    total_comments_count = Comment.visible_objects() \
        .filter(author=user, created_at__gte=datetime.utcnow() - timedelta(hours=24)) \
        .count()

    return total_comments_count < comments_per_day_limit


