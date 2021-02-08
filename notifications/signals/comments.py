from django.db.models.signals import post_save
from django.dispatch import receiver
from django_q.tasks import async_task

from club import settings
from notifications.telegram.common import Chat, send_telegram_message, render_html_message, CLUB_ONLINE, ADMIN_CHAT
from comments.models import Comment
from common.regexp import USERNAME_RE
from posts.models.subscriptions import PostSubscription
from users.models.user import User


@receiver(post_save, sender=Comment)
def create_or_update_comment(sender, instance, created, **kwargs):
    if not created:
        return None  # we're not interested in updates

    async_task(async_create_or_update_comment, instance)


def async_create_or_update_comment(comment):
    notified_user_ids = set()

    # notify post subscribers
    post_subscribers = PostSubscription.post_subscribers(comment.post)
    for post_subscriber in post_subscribers:
        if post_subscriber.user.telegram_id and comment.author != post_subscriber.user:
            template = "comment_to_post.html" if post_subscriber.user == comment.post.author else "comment_to_post_announce.html"
            send_telegram_message(
                chat=Chat(id=post_subscriber.user.telegram_id),
                text=render_html_message(template, comment=comment),
            )
            notified_user_ids.add(post_subscriber.user.id)

    # on reply — notify thread author (do not notify yourself)
    if comment.reply_to:
        thread_author = comment.reply_to.author
        if thread_author.telegram_id and comment.author != thread_author and thread_author.id not in notified_user_ids:
            send_telegram_message(
                chat=Chat(id=thread_author.telegram_id),
                text=render_html_message("comment_to_thread.html", comment=comment),
            )
            notified_user_ids.add(thread_author.id)

    # post top level comments to online channel
    if not comment.reply_to:
        send_telegram_message(
            chat=CLUB_ONLINE,
            text=render_html_message("comment_to_post_announce.html", comment=comment),
        )

    # parse @nicknames and notify their users
    for username in USERNAME_RE.findall(comment.text):
        if username == settings.MODERATOR_USERNAME:
            send_telegram_message(
                chat=ADMIN_CHAT,
                text=render_html_message("moderator_mention.html", comment=comment),
            )
            continue

        user = User.objects.filter(slug=username).first()
        if user and user.telegram_id and user.id not in notified_user_ids:
            send_telegram_message(
                chat=Chat(id=user.telegram_id),
                text=render_html_message("comment_mention.html", comment=comment),
            )
            notified_user_ids.add(user.id)
