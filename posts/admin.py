from django.contrib import admin

from posts.models.linked import LinkedPost
from posts.models.post import Post


class PostsAdmin(admin.ModelAdmin):
    list_display = (
        "slug",
        "title",
        "created_at",
        "published_at",
        "comment_count",
        "view_count",
        "upvotes",
        "is_visible",
        "is_commentable",
        "is_approved_by_moderator",
        "is_public",
    )
    ordering = ("-created_at",)
    search_fields = ["title", "slug"]


admin.site.register(Post, PostsAdmin)


class LinkedPostsAdmin(admin.ModelAdmin):
    list_display = (
        "post_from",
        "post_to",
        "user",
        "created_at",
    )
    ordering = ("-created_at",)


admin.site.register(LinkedPost, LinkedPostsAdmin)
