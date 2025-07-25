import telegram

from django.db.models.signals import post_save
from django.dispatch import receiver
from django_q.tasks import async_task

from notifications.telegram.common import ADMIN_CHAT, send_telegram_message, render_html_message, Chat
from posts.models.post import Post
from users.models.user import User


@receiver(post_save, sender=Post)
def create_or_update_post(sender, instance, created, **kwargs):
    if "label_code" in instance.changed_fields:
        async_task(async_label_changed, instance)

    if "coauthors" in instance.changed_fields:
        async_task(async_coauthors_changed, instance)

    return None


def async_label_changed(post):
    moderator_template = "moderator_label_removed.html" if post.label_code is None else "moderator_label_set.html"
    send_telegram_message(
        chat=ADMIN_CHAT,
        text=render_html_message(moderator_template, post=post),
        parse_mode=telegram.ParseMode.HTML,
    )
    if post.label_code is not None and post.label['notify'] and post.author.telegram_id:
        send_telegram_message(
            chat=Chat(id=post.author.telegram_id),
            text=render_html_message("post_label.html", post=post),
            parse_mode=telegram.ParseMode.HTML,
        )


def notify_users(users, template, post):
    for username in users:
        user = User.objects.filter(slug=username).first()
        if user and user.telegram_id:
            send_telegram_message(
                chat=Chat(id=user.telegram_id),
                text=render_html_message(template, post=post),
            )


def async_coauthors_changed(post):
    old = set()
    history = list(post.history.all()[:2])
    if len(history) == 2:
        old = set(history[1].coauthors)
    new = set(post.coauthors)
    added = new - old
    removed = old - new
    notify_users(added, "coauthor_added.html", post)
    notify_users(removed, "coauthor_removed.html", post)
