from django.shortcuts import get_object_or_404

from posts.rss import NewPostsRss
from posts.models.post import Post
from users.models.user import User


class UserPostsRss(NewPostsRss):
    def get_object(self, _, user_slug=None):
        return get_object_or_404(User, slug=user_slug)
    
    def link(self, user):
        return f"/user/{user.slug}/posts.rss"
    
    def title(self, user):
        return f"Вастрик.Клуб: Посты {user.slug}"

    def items(self, user):
        return Post.visible_objects()\
           .filter(is_approved_by_moderator=True)\
           .filter(author=user) \
           .exclude(type=Post.TYPE_INTRO)\
           .order_by("-published_at", "-created_at")[:self.limit]

    def item_title(self, item):
        title = item.title
        if item.prefix:
            title = f"{item.prefix} " + title
        if not item.is_public:
            title += " 🔒"
        return title

    def item_description(self, item):
        return item.description
