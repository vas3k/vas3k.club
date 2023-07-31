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
        "network_group",
        "last_activity_at",
        "is_visible",
        "is_open_for_posting",
        "is_bot_active",
        "index",
    )
    ordering = ("title",)
    search_fields = ["title", "description", "slug"]


admin.site.register(Room, RoomsAdmin)
