from datetime import datetime
from uuid import uuid4

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField, SearchVector, SearchRank, SearchQuery
from django.db import models
from django.db.models import F

from comments.models import Comment
from posts.models.post import Post
from users.models.user import User
from users.models.tags import UserTag


class SearchIndex(models.Model):
    TYPE_POST = "post"
    TYPE_COMMENT = "comment"
    TYPE_USER = "user"
    TYPES = [
        (TYPE_POST, TYPE_POST),
        (TYPE_COMMENT, TYPE_COMMENT),
        (TYPE_USER, TYPE_USER),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    type = models.CharField(max_length=32, choices=TYPES, null=True, db_index=True)
    post = models.ForeignKey(Post, related_name="index", null=True, db_index=True, on_delete=models.SET_NULL)
    comment = models.ForeignKey(Comment, related_name="index", null=True, db_index=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(User, related_name="index", null=True, db_index=True, on_delete=models.SET_NULL)

    tags = ArrayField(models.CharField(max_length=32), null=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    index = SearchVectorField(null=False, editable=False)

    class Meta:
        db_table = "search_index"
        ordering = ["-created_at"]
        indexes = [
            GinIndex(fields=["index"], fastupdate=False),
        ]

    @classmethod
    def search(cls, query):
        query = SearchQuery(query, config="russian")

        return SearchIndex.objects\
            .annotate(rank=SearchRank(F("index"), query))\
            .filter(index=query, rank__gte=0.1)

    @classmethod
    def update_comment_index(cls, comment):
        vector = SearchVector("text", weight="B", config="russian") \
                 + SearchVector("author__slug", weight="C", config="russian")

        SearchIndex.objects.update_or_create(
            comment=comment,
            defaults=dict(
                type=SearchIndex.TYPE_COMMENT,
                index=Comment.objects
                .annotate(vector=vector)
                .filter(id=comment.id)
                .values_list("vector", flat=True)
                .first(),
                created_at=comment.created_at,
                updated_at=datetime.utcnow(),
            )
        )

    @classmethod
    def update_post_index(cls, post):
        vector = SearchVector("title", weight="A", config="russian") \
                 + SearchVector("text", weight="B", config="russian") \
                 + SearchVector("author__slug", weight="C", config="russian") \
                 + SearchVector("topic__name", weight="C", config="russian")

        if post.is_searchable:
            SearchIndex.objects.update_or_create(
                post=post,
                defaults=dict(
                    type=SearchIndex.TYPE_POST,
                    index=Post.objects
                    .annotate(vector=vector)
                    .filter(id=post.id)
                    .values_list("vector", flat=True)
                    .first(),
                    created_at=post.created_at,
                    updated_at=datetime.utcnow(),
                )
            )
        else:
            SearchIndex.objects.filter(post=post).delete()

    @classmethod
    def update_user_index(cls, user):
        vector = SearchVector("slug", weight="A", config="russian") \
                 + SearchVector("full_name", weight="A", config="russian") \
                 + SearchVector("bio", weight="B", config="russian") \
                 + SearchVector("company", weight="B", config="russian") \
                 + SearchVector("country", weight="C", config="russian") \
                 + SearchVector("city", weight="C", config="russian")

        user_index = User.objects\
            .annotate(vector=vector)\
            .filter(id=user.id)\
            .values_list("vector", flat=True)\
            .first()

        intro_index = Post.objects.filter(author=user, type=Post.TYPE_INTRO)\
            .annotate(vector=SearchVector("text", weight="B", config="russian"))\
            .values_list("vector", flat=True)\
            .first()

        if user.moderation_status == User.MODERATION_STATUS_APPROVED:
            SearchIndex.objects.update_or_create(
                user=user,
                defaults=dict(
                    type=SearchIndex.TYPE_USER,
                    index=(user_index or "") + " " + (intro_index or ""),
                    created_at=user.created_at,
                    updated_at=datetime.utcnow(),
                )
            )
        else:
            SearchIndex.objects.filter(user=user).delete()

    @classmethod
    def update_user_tags(cls, user):
        if user.moderation_status == User.MODERATION_STATUS_APPROVED:
            SearchIndex.objects.filter(user=user).update(
                tags=list(UserTag.objects.filter(user=user).values_list("tag", flat=True)),
            )
