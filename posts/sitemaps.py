from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from posts.models.post import Post


class PublicPostsSitemap(Sitemap):
    def items(self):
        return Post.visible_objects()\
            .filter(is_public=True)\
            .select_related(None)\
            .values("type", "slug", "updated_at")

    def location(self, obj):
        return reverse("show_post", kwargs={"post_type": obj["type"], "post_slug": obj["slug"]})

    def lastmod(self, obj):
        return obj["updated_at"]


sitemaps = {
    "public_posts": PublicPostsSitemap,
}
