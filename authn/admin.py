from django.contrib import admin

from authn.models import Apps


class AppsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "owner",
        "redirect_urls",
        "service_token",
    )
    ordering = ("id",)


admin.site.register(Apps, AppsAdmin)
