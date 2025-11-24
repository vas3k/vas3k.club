from notifications.telegram.common import send_telegram_message, VIBES_CHAT, ADMIN_CHAT, render_html_message


def notify_moderators_on_mention(comment):
    for chat in [ADMIN_CHAT, VIBES_CHAT]:
        send_telegram_message(
            chat=chat,
            text=render_html_message("moderator_mention.html", comment=comment),
        )
