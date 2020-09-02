from uuid import uuid4

from django.db import models

from posts.models.post import Post
from users.models.user import User


class PostBookmark(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(User, related_name="bookmarks", db_index=True, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name="bookmarks", db_index=True, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "post_bookmarks"
