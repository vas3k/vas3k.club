from django.contrib import admin

from posts.models.linked import LinkedPost
from posts.models.post import Post
from posts.models.topics import Topic


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


class TopicsAdmin(admin.ModelAdmin):
    list_display = (
        "slug",
        "name",
        "icon",
        "color",
        "style",
        "chat_name",
        "last_activity_at",
        "is_visible",
        "is_visible_in_feeds",
    )
    ordering = ("slug",)
    search_fields = ["slug", "name"]


admin.site.register(Topic, TopicsAdmin)


class LinkedPostsAdmin(admin.ModelAdmin):
    list_display = (
        "post_from",
        "post_to",
        "user",
        "created_at",
    )
    ordering = ("-created_at",)


admin.site.register(LinkedPost, LinkedPostsAdmin)
