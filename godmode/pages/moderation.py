from django.template.loader import render_to_string

from posts.models.post import Post
from users.models.user import User


def moderation(request, admin_page):
    users = User.objects.filter(moderation_status=User.MODERATION_STATUS_ON_REVIEW).order_by("created_at")
    posts = Post.objects.filter(moderation_status=Post.MODERATION_PENDING).order_by("created_at")
    moderators = User.objects.filter(roles__contains=[User.ROLE_MODERATOR]).order_by("created_at")
    return render_to_string("godmode/pages/moderation.html", {
        "users": users,
        "posts": posts,
        "moderators": moderators,
    }, request=request)
