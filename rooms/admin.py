from django.contrib import admin

from rooms.models import Room


class RoomsAdmin(admin.ModelAdmin):
    list_display = (
        "slug",
        "title",
        "subtitle",
        "image",
        "icon",
        "color",
        "chat_name",
        "send_new_posts_to_chat",
        "send_new_comments_to_chat",
        "network_group",
        "last_activity_at",
        "is_visible",
        "is_open_for_posting",
        "index",
    )
    ordering = ("title",)
    search_fields = ["title", "description", "slug"]


admin.site.register(Room, RoomsAdmin)
