from django.contrib import admin

from tags.models import Tag, UserTag


class TagsAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "group",
        "name",
        "index",
        "is_visible",
    )
    ordering = ("name", "group")


admin.site.register(Tag, TagsAdmin)
admin.site.register(UserTag)
