from django.contrib import admin

from askbot.models import UserAskBan


class UserAskBanAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "banned_until",
        "ban_reason"
    )
    search_fields = ["user"]


admin.site.register(UserAskBan, UserAskBanAdmin)
