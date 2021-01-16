import re

from django.db import models
from django.db.models import Q

from posts.models.post import Post
from users.models.user import User

CLUB_POST_URL_RE = re.compile(r"https:\/\/vas3k.club\/[\S]+?\/([\S]+?)\/")


class LinkedPost(models.Model):
    post_from = models.ForeignKey(Post, related_name="linked_posts_from", db_index=True, on_delete=models.CASCADE)
    post_to = models.ForeignKey(Post, related_name="linked_posts_to", db_index=True, on_delete=models.CASCADE)

    user = models.ForeignKey(User, related_name="linked_posts", null=True, on_delete=models.SET_NULL)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "linked_posts"
        unique_together = [["post_from", "post_to"]]

    @classmethod
    def link(cls, user, post_from, post_to):
        if not post_from.is_visible or not post_to.is_visible:
            return None, False

        if post_from.id == post_to.id:
            return None, False

        linked_post, is_created = LinkedPost.objects.get_or_create(
            post_from=post_from,
            post_to=post_to,
            defaults=dict(
                user=user,
            )
        )
        return linked_post, is_created

    @classmethod
    def create_links_from_text(cls, post_from, text):
        links = CLUB_POST_URL_RE.findall(text)
        for post_slug in links:
            post_to = Post.visible_objects().filter(slug=post_slug).first()
            if post_to:
                cls.link(post_from.author, post_from, post_to)

    @classmethod
    def links_for_post(cls, post):
        return LinkedPost.objects.filter(Q(post_from=post) | Q(post_to=post)).select_related("post_from", "post_to")
