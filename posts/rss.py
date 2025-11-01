from datetime import datetime, timedelta

from django.contrib.syndication.views import Feed

from posts.models.post import Post


class NewPostsRss(Feed):
    title = "Вастрик.Клуб: Новые посты"
    link = "/posts.rss"
    description = ""
    limit = 20

    def items(self):
        recent_cutoff = datetime.utcnow() - timedelta(days=30)
        return (
            Post.visible_objects()
            .filter(
                moderation_status=Post.MODERATION_APPROVED,
                published_at__gte=recent_cutoff,
                is_public=True,
            )
            .exclude(type=Post.TYPE_INTRO)
            .order_by("-published_at", "-created_at")[: self.limit]
        )

    def item_title(self, item):
        title = item.title
        if item.prefix:
            title = f"{item.prefix} " + title
        if not item.is_public:
            title += " 🔒"
        return title

    def item_description(self, item):
        return item.description

    def item_pubdate(self, item):
        return item.published_at

    def item_author_name(self, item):
        return item.author.slug
