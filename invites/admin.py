from django.contrib import admin

from invites.models import Invite


class InvitesAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "user",
        "created_at",
        "used_at",
        "invited_email",
        "invited_user",
    )
    ordering = ("-created_at",)


admin.site.register(Invite, InvitesAdmin)
