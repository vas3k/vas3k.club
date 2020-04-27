import telegram
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_q.tasks import async_task

from bot.common import Chat, ADMIN_CHAT, send_telegram_message, render_html_message, CLUB_CHAT
from comments.models import Comment


@receiver(post_save, sender=Comment)
def create_or_update_comment(sender, instance, created, **kwargs):
    if not created:
        return None  # we're not interested in updates

    async_task(async_create_or_update_comment, instance, created)


def async_create_or_update_comment(comment, is_created):
    # notify admins
    send_telegram_message(
        chat=ADMIN_CHAT,
        text=render_html_message("moderator_comment.html", comment=comment),
        parse_mode=telegram.ParseMode.HTML,
    )

    # notify post author
    post_author = comment.post.author
    if post_author.telegram_id and comment.author != post_author:
        send_telegram_message(
            chat=Chat(id=comment.post.author.telegram_id),
            text=render_html_message("comment_to_post.html", comment=comment),
            parse_mode=telegram.ParseMode.HTML,
        )

    # on reply — notify thread author (do not notify yourself)
    if comment.reply_to:
        thread_author = comment.reply_to.author
        if comment.reply_to_id and thread_author.telegram_id and comment.author != thread_author:
            send_telegram_message(
                chat=Chat(id=comment.reply_to.author.telegram_id),
                text=render_html_message("comment_to_thread.html", comment=comment),
                parse_mode=telegram.ParseMode.HTML,
            )

    # post first level comments to club chat
    # if not comment.reply_to:
    #     send_telegram_message(
    #         chat=CLUB_CHAT,
    #         text=render_html_message("comment_to_post_announce.html", comment=comment),
    #         parse_mode=telegram.ParseMode.HTML,
    #     )

    # TODO: parse if comment starts with @nickname and notify users
