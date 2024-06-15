from django.contrib import admin

from helpdeskbot.models import HelpDeskUser, Answer, Question


class HelpDeskUserAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "banned_until",
        "ban_reason"
    )
    search_fields = ["user"]


admin.site.register(HelpDeskUser, HelpDeskUserAdmin)


class HelpDeskQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "created_at",
        "json_text",
        "channel_msg_id",
        "discussion_msg_id",
        "room",
        "room_chat_msg_id",
    )
    search_fields = ["json_text"]


admin.site.register(Question, HelpDeskQuestionAdmin)


class HelpDeskAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "user_name",
        "question",
        "created_at",
        "text",
    )
    search_fields = ["user_name", "text"]


admin.site.register(Answer, HelpDeskAnswerAdmin)
