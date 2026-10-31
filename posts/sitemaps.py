from django.contrib.sitemaps import Sitemap

from posts.models.post import Post


class PublicPostsSitemap(Sitemap):
    def items(self):
        return Post.visible_objects()\
            .filter(is_public=True)\
            .select_related(None)\
            .only("id", "type", "slug", "updated_at")

    def lastmod(self, obj: Post):
        return obj.updated_at


sitemaps = {
    "public_posts": PublicPostsSitemap,
}
