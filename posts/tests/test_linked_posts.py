from datetime import datetime, timedelta

from django.test import TestCase

from posts.models.linked import LinkedPost
from posts.models.post import Post
from users.models.user import User


class TestCreateLinksFromText(TestCase):
    def setUp(self):
        self.author = User.objects.create(
            email="linked_author@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            slug="linked_author",
        )
        self.target_posts = []
        for i in range(5):
            post = Post.objects.create(
                type=Post.TYPE_POST,
                slug=f"target_{i}",
                title=f"Target {i}",
                text="target body",
                author=self.author,
                visibility=Post.VISIBILITY_EVERYWHERE,
            )
            self.target_posts.append(post)

        self.source_post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="source_post",
            title="Source",
            text="source body",
            author=self.author,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )

    def test_creates_linked_posts_from_urls(self):
        text = " ".join(
            f"https://vas3k.club/post/{p.slug}/" for p in self.target_posts
        )

        LinkedPost.create_links_from_text(self.source_post, text)

        self.assertEqual(LinkedPost.objects.count(), 5)
        for target in self.target_posts:
            self.assertTrue(
                LinkedPost.objects.filter(post_from=self.source_post, post_to=target).exists()
            )

    def test_no_queries_when_no_links(self):
        with self.assertNumQueries(0):
            LinkedPost.create_links_from_text(self.source_post, "no links here")

        self.assertEqual(LinkedPost.objects.count(), 0)

    def test_deduplicates_urls(self):
        slug = self.target_posts[0].slug
        text = f"https://vas3k.club/post/{slug}/ and again https://vas3k.club/post/{slug}/"

        LinkedPost.create_links_from_text(self.source_post, text)

        self.assertEqual(LinkedPost.objects.count(), 1)

    def test_ignores_nonexistent_slugs(self):
        text = "https://vas3k.club/post/nonexistent_slug_xyz/"

        LinkedPost.create_links_from_text(self.source_post, text)

        self.assertEqual(LinkedPost.objects.count(), 0)

    def test_ignores_draft_posts(self):
        draft = Post.objects.create(
            type=Post.TYPE_POST,
            slug="draft_post",
            title="Draft",
            text="draft body",
            author=self.author,
            visibility=Post.VISIBILITY_DRAFT,
        )
        text = f"https://vas3k.club/post/{draft.slug}/"

        LinkedPost.create_links_from_text(self.source_post, text)

        self.assertEqual(LinkedPost.objects.count(), 0)
