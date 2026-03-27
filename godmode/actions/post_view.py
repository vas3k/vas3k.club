from django.shortcuts import redirect

from posts.models.post import Post


def view_post_action(request, post: Post, **context):
    return redirect(post.get_absolute_url())
