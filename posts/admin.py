from django.contrib import admin

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


admin.site.register(Post, PostsAdmin)
