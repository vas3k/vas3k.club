from django.contrib import admin

from misc.models import ProTip, NetworkGroup


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

