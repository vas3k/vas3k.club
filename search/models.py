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
from tags.models import UserTag


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

    created_at = models.DateTimeField(db_index=True)
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
        sq_simple = SearchQuery(query, config="simple", search_type="websearch")
        sq_stemmed = SearchQuery(query, config="russian", search_type="websearch")

        return SearchIndex.objects\
            .annotate(rank=SearchRank(F("index"), sq_simple) * 2 + SearchRank(F("index"), sq_stemmed))\
            .filter(index=sq_simple | sq_stemmed, rank__gte=0.1)

    @classmethod
    def update_comment_index(cls, comment):
        vector = _multi_search_vector("text", weight="B") \
                 + _multi_search_vector("author__slug", weight="C")

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
        vector = _multi_search_vector("title", weight="A") \
                 + _multi_search_vector("text", weight="B") \
                 + _multi_search_vector("author__slug", weight="C") \
                 + _multi_search_vector("room__title", weight="C")

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
                    created_at=post.published_at or post.created_at,
                    updated_at=datetime.utcnow(),
                )
            )
        else:
            SearchIndex.objects.filter(post=post).delete()

    @classmethod
    def update_user_index(cls, user):
        vector = _multi_search_vector("slug", weight="A") \
                 + _multi_search_vector("full_name", weight="A") \
                 + _multi_search_vector("email", weight="A") \
                 + _multi_search_vector("bio", weight="B") \
                 + _multi_search_vector("company", weight="B") \
                 + _multi_search_vector("country", weight="C") \
                 + _multi_search_vector("city", weight="C") \
                 + _multi_search_vector("contact", weight="C")

        user_index = User.objects\
            .annotate(vector=vector)\
            .filter(id=user.id)\
            .values_list("vector", flat=True)\
            .first()

        intro_index = Post.objects.filter(author=user, type=Post.TYPE_INTRO)\
            .annotate(vector=_multi_search_vector("text", weight="B"))\
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
                tags=list(UserTag.objects.filter(user=user).values_list("tag", flat=True))[:100],
            )


def _multi_search_vector(*expressions, weight=None):
    return (
        SearchVector(*expressions, weight=weight, config="russian") +
        SearchVector(*expressions, weight=weight, config="simple")
    )
