from django.contrib.sitemaps import Sitemap
from .models import Post


class PublicPostsSitemap(Sitemap):
    def items(self):
        return Post.objects.filter(is_public=True)

    def lastmod(self, obj: Post):
        return obj.updated_at
