from django.contrib import admin

from users.models.achievements import Achievement, UserAchievement
from users.models.friends import Friend
from users.models.mute import Muted
from users.models.notes import UserNote
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
    search_fields = ["slug", "email", "full_name"]


admin.site.register(User, UsersAdmin)


class AchievementsAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "image",
        "description",
        "style",
        "index",
        "is_visible",
    )
    ordering = ("index",)
    search_fields = ["code", "name"]


admin.site.register(Achievement, AchievementsAdmin)


class UserAchievementsAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "achievement",
        "created_at",
    )
    ordering = ("-created_at",)


admin.site.register(UserAchievement, UserAchievementsAdmin)


class FriendsAdmin(admin.ModelAdmin):
    list_display = (
        "user_from",
        "user_to",
        "created_at",
        "is_subscribed_to_posts",
        "is_subscribed_to_comments",
    )
    ordering = ("-created_at",)


admin.site.register(Friend, FriendsAdmin)


class MutedAdmin(admin.ModelAdmin):
    list_display = (
        "user_from",
        "user_to",
        "created_at",
        "comment",
    )
    ordering = ("-created_at",)


admin.site.register(Muted, MutedAdmin)


class UserNotesAdmin(admin.ModelAdmin):
    list_display = (
        "user_to",
        "user_from",
        "text",
        "created_at",
    )
    ordering = ("-created_at",)


admin.site.register(UserNote, UserNotesAdmin)
