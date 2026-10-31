from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from posts.models.post import Post
from posts.sitemaps import PublicPostsSitemap
from users.models.user import User


class TestPublicPostsSitemap(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = datetime.utcnow()
        author = User.objects.create(
            slug="sitemap-author",
            email="sitemap-author@example.com",
            full_name="Sitemap author",
            membership_started_at=now - timedelta(days=1),
            membership_expires_at=now + timedelta(days=30),
        )
        cls.posts = {}

        for slug, post_type, is_public, visibility in [
            ("sitemap-post", Post.TYPE_POST, True, Post.VISIBILITY_EVERYWHERE),
            ("sitemap-question", Post.TYPE_QUESTION, True, Post.VISIBILITY_EVERYWHERE),
            ("sitemap-private", Post.TYPE_POST, False, Post.VISIBILITY_EVERYWHERE),
            ("sitemap-draft", Post.TYPE_POST, True, Post.VISIBILITY_DRAFT),
            ("sitemap-link", Post.TYPE_POST, True, Post.VISIBILITY_LINK_ONLY),
        ]:
            cls.posts[slug] = Post.objects.create(
                author=author,
                slug=slug,
                type=post_type,
                title=slug,
                text="Large post body " * 10000,
                html="<p>Large post body</p>" * 10000,
                is_public=is_public,
                visibility=visibility,
            )

    def test_public_urls_and_dates_without_loading_post_models(self):
        expected = {
            f"https://vas3k.club{post.get_absolute_url()}": post.updated_at
            for slug, post in self.posts.items()
            if slug in {"sitemap-post", "sitemap-question"}
        }

        with patch.object(Post, "from_db", side_effect=AssertionError("Sitemap must not instantiate Post")):
            with self.assertNumQueries(2):
                urls = PublicPostsSitemap().get_urls(
                    site=SimpleNamespace(domain="vas3k.club"),
                    protocol="https",
                )

        self.assertEqual({url["location"]: url["lastmod"] for url in urls}, expected)
