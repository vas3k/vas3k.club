from django.contrib import admin

from comments.models import Comment


class CommentsAdmin(admin.ModelAdmin):
    list_display = (
        "author",
        "post",
        "reply_to",
        "title",
        "ipaddress",
        "created_at",
        "upvotes",
        "is_visible",
        "is_deleted",
    )
    ordering = ("-created_at",)


admin.site.register(Comment, CommentsAdmin)
