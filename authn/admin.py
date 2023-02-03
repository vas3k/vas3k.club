from django.contrib import admin

from authn.models import Apps


class AppsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "owner",
        "jwt_secret",
        "jwt_algorithm",
        "jwt_expire_hours",
        "redirect_urls",
        "service_token",
    )
    ordering = ("id",)


admin.site.register(Apps, AppsAdmin)
