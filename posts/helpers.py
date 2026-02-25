import re
from datetime import datetime, timedelta

from django.http import Http404

from posts.models.post import Post

POST_TYPE_ALL = "all"

ORDERING_ACTIVITY = "activity"
ORDERING_NEW = "new"
ORDERING_HOT = "hot"
ORDERING_TOP = "top"
ORDERING_TOP_WEEK = "top_week"
ORDERING_TOP_MONTH = "top_month"
ORDERING_TOP_YEAR = "top_year"

MARKDOWN_IMAGES_RE = re.compile(r"!\[*\]\((.+)\)")


def extract_any_image(post):
    if post.image and post.type != Post.TYPE_LINK:
        return post.image

    text_images = MARKDOWN_IMAGES_RE.findall(post.text)
    if text_images:
        return text_images[0]

    return None


def get_feed_posts(user=None, post_type=POST_TYPE_ALL, room=None,
                   label_code=None, ordering=ORDERING_ACTIVITY, ordering_param=None):
    if user:
        posts = Post.objects_for_user(user)
    else:
        posts = Post.visible_objects()

    if post_type != POST_TYPE_ALL:
        posts = posts.filter(type=post_type)

    if room:
        posts = posts.filter(room=room)

    if label_code:
        posts = posts.filter(label_code=label_code)

    if user:
        posts = posts.exclude(author__muted_to__user_from=user)
        if not room and ordering in [ORDERING_NEW, ORDERING_HOT, ORDERING_ACTIVITY]:
            posts = posts.exclude(room__muted_users__user=user)

    if not user:
        posts = posts.exclude(is_public=False).exclude(type=Post.TYPE_INTRO)

    if not room and not label_code:
        posts = posts.exclude(is_room_only=True)

    return sort_feed(posts, ordering, ordering_param)


def sort_feed(posts, ordering, ordering_param=None):
    if not ordering:
        return posts

    if ordering == ORDERING_ACTIVITY:
        return posts.order_by("-last_activity_at")

    elif ordering == ORDERING_NEW:
        return posts.order_by("-published_at", "-created_at")

    elif ordering == ORDERING_TOP:
        return posts.order_by("-upvotes")

    elif ordering == ORDERING_HOT:
        return posts.order_by("-hotness")

    elif ordering == ORDERING_TOP_WEEK:
        return posts.filter(
            published_at__gte=datetime.utcnow() - timedelta(days=7)
        ).order_by("-upvotes")

    elif ordering == ORDERING_TOP_MONTH:
        if ordering_param:
            try:
                start_date = datetime.strptime(ordering_param, "%Y-%m")
                end_date = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1)
            except ValueError:
                raise Http404()
        else:
            start_date = datetime.utcnow() - timedelta(days=31)
            end_date = datetime.utcnow()

        return posts.filter(
            published_at__gte=start_date,
            published_at__lt=end_date,
        ).order_by("-upvotes")

    elif ordering == ORDERING_TOP_YEAR:
        if ordering_param:
            try:
                start_date = datetime.strptime(ordering_param, "%Y")
                end_date = start_date.replace(year=start_date.year + 1)
            except ValueError:
                raise Http404()
        else:
            start_date = datetime.utcnow() - timedelta(days=365)
            end_date = datetime.utcnow()

        return posts.filter(
            published_at__gte=start_date,
            published_at__lt=end_date,
        ).order_by("-upvotes")
    else:
        raise Http404()
