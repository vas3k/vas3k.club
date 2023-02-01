from django.contrib import admin

from users.models.achievements import Achievement, UserAchievement
from users.models.friends import Friend
from users.models.mute import Muted
from users.models.user import User


class UsersAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "slug",
        "full_name",
        "city",
        "country",
        "membership_started_at",
        "membership_expires_at",
        "email_digest_type",
        "is_email_verified",
        "is_email_unsubscribed",
        "is_banned_until",
        "moderation_status",
    )
    ordering = ("-created_at",)


admin.site.register(User, UsersAdmin)

admin.site.register(Achievement)
admin.site.register(UserAchievement)
admin.site.register(Friend)
admin.site.register(Muted)
