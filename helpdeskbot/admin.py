from django.contrib import admin

from helpdeskbot.models import HelpDeskUser


class HelpDeskUserAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "banned_until",
        "ban_reason"
    )
    search_fields = ["user"]


admin.site.register(HelpDeskUser, HelpDeskUserAdmin)
