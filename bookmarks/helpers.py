from posts.models.post import Post


def get_user_bookmarks(user):
    return Post.objects_for_user(user)\
        .filter(bookmarks__user=user, deleted_at__isnull=True)\
        .order_by('-bookmarks__created_at')
