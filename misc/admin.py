from django.contrib import admin

from misc.models import ProTip, NetworkGroup, NetworkItem


class ProTipsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "created_at",
        "updated_at",
        "is_visible",
    )
    ordering = ("-created_at",)
    search_fields = ["title", "text"]


admin.site.register(ProTip, ProTipsAdmin)


class NetworkGroupAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "index",
        "is_visible",
    )
    ordering = ("index",)
    search_fields = ["title"]


admin.site.register(NetworkGroup, NetworkGroupAdmin)


class NetworkItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "group",
        "url",
        "index",
    )
    ordering = ("index",)
    search_fields = ["title", "description"]


admin.site.register(NetworkItem, NetworkItemAdmin)

