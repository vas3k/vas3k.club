from django.contrib import admin

from misc.models import ProTip


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
