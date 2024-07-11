from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404

from posts.models.post import Post
from users.models.user import User


class NewPostsRss(Feed):
    description = ""
    limit = 20

    def get_object(self, _, user_slug=None):
        if user_slug is None:
            return None
        
        return get_object_or_404(User, slug=user_slug)
    
    def link(self, user):
        if user is None:
            return "/posts.rss"
        
        return f"/user/{user.slug}/posts.rss"
    
    def title(self, user):
        if user is None:
            return "Вастрик.Клуб: Новые посты"
        
        return f"Вастрик.Клуб: Посты {user.slug}"

    def items(self, user):
        res = Post.visible_objects().filter(is_approved_by_moderator=True)
        
        if user is not None:
            res = res.filter(author=user)
           
        return res.exclude(type=Post.TYPE_INTRO).order_by("-published_at", "-created_at")[:self.limit]

    def item_title(self, item):
        title = item.title
        if item.prefix:
            title = f"{item.prefix} " + title
        if not item.is_public:
            title += " 🔒"
        return title

    def item_description(self, item):
        return item.description
