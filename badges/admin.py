from django.contrib import admin

from badges.models import Badge, UserBadge


class BadgesAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "description",
        "price_days",
        "created_at",
        "is_visible",
    )
    ordering = ("-created_at",)
    search_fields = ["title"]


admin.site.register(Badge, BadgesAdmin)


class UserBadgesAdmin(admin.ModelAdmin):
    list_display = (
        "badge",
        "from_user",
        "to_user",
        "post",
        "comment",
        "created_at",
    )
    ordering = ("-created_at",)


admin.site.register(UserBadge, UserBadgesAdmin)
