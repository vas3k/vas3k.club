import telegram
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django_q.tasks import async_task

from club import settings
from notifications.telegram.common import Chat, send_telegram_message, render_html_message, CLUB_ONLINE, ADMIN_CHAT
from comments.models import Comment
from common.regexp import USERNAME_RE
from posts.models.subscriptions import PostSubscription
from users.models.friends import Friend
from users.models.mute import Muted
from users.models.user import User


@receiver(post_save, sender=Comment)
def create_or_update_comment(sender, instance, created, **kwargs):
    if not created:
        return None  # we're not interested in comment updates

    async_task(async_create_or_update_comment, instance)


def async_create_or_update_comment(comment):
    notified_user_ids = set()
    muted_author_user_ids = set(
        Muted.who_muted_user(comment.author_id).values_list("user_from_id", flat=True)
    )

    comment_url = settings.APP_HOST + reverse("show_comment", kwargs={
        "post_slug": comment.post.slug,
        "comment_id": comment.id,
    })
    comment_reply_markup = telegram.InlineKeyboardMarkup([
        [
            telegram.InlineKeyboardButton("👍", callback_data=f"upvote_comment:{comment.id}"),
            telegram.InlineKeyboardButton("🔗", url=comment_url),
            telegram.InlineKeyboardButton("🔕", callback_data=f"unsubscribe:{comment.post_id}"),
        ],
    ])

    # notify post subscribers
    post_subscribers = PostSubscription.post_subscribers(comment.post)
    for post_subscriber in post_subscribers:
        if post_subscriber.user_id in muted_author_user_ids:
            continue

        if post_subscriber.user.telegram_id and comment.author != post_subscriber.user:
            # respect subscription type (i.e. all comments vs top level only)
            if post_subscriber.type == PostSubscription.TYPE_ALL_COMMENTS \
                    or (post_subscriber.type == PostSubscription.TYPE_TOP_LEVEL_ONLY and not comment.reply_to_id):
                send_telegram_message(
                    chat=Chat(id=post_subscriber.user.telegram_id),
                    text=render_html_message("comment_to_post.html", comment=comment),
                    reply_markup=comment_reply_markup,
                )
                notified_user_ids.add(post_subscriber.user.id)

    # notify thread author on reply (note: do not notify yourself)
    if comment.reply_to:
        thread_author = comment.reply_to.author
        if thread_author.telegram_id \
                and comment.author != thread_author \
                and thread_author.id not in notified_user_ids \
                and thread_author.id not in muted_author_user_ids:
            send_telegram_message(
                chat=Chat(id=thread_author.telegram_id),
                text=render_html_message("comment_to_thread.html", comment=comment),
                reply_markup=comment_reply_markup,
            )
            notified_user_ids.add(thread_author.id)

    # post top level comments to "online" channel
    if not comment.reply_to and comment.post.is_visible and comment.post.is_visible_in_feeds:
        send_telegram_message(
            chat=CLUB_ONLINE,
            text=render_html_message("channel_comment_announce.html", comment=comment),
        )

    # post top level comments to "rooms" (if necessary)
    if not comment.reply_to and comment.post.is_visible:
        if comment.post.room_id and comment.post.room.chat_id and comment.post.room.send_new_comments_to_chat:
            send_telegram_message(
                chat=Chat(id=comment.post.room.chat_id),
                text=render_html_message("channel_comment_announce.html", comment=comment),
            )

    # notify friends about your comments (not replies)
    if not comment.reply_to:
        friends = Friend.friends_for_user(comment.author)
        for friend in friends:
            if friend.user_from.telegram_id \
                    and friend.is_subscribed_to_comments \
                    and friend.user_from.id not in notified_user_ids:
                send_telegram_message(
                    chat=Chat(id=friend.user_from.telegram_id),
                    text=render_html_message("friend_comment.html", comment=comment),
                    reply_markup=comment_reply_markup,
                )
                notified_user_ids.add(friend.user_from.id)

    # parse @nicknames and notify their users
    for username in USERNAME_RE.findall(comment.text):
        if username == settings.MODERATOR_USERNAME:
            send_telegram_message(
                chat=ADMIN_CHAT,
                text=render_html_message("moderator_mention.html", comment=comment),
            )
            continue

        user = User.objects.filter(slug=username).first()
        if not user:
            continue

        if user.id in muted_author_user_ids:
            continue

        if user.telegram_id and user.id not in notified_user_ids:
            send_telegram_message(
                chat=Chat(id=user.telegram_id),
                text=render_html_message("comment_mention.html", comment=comment),
                reply_markup=comment_reply_markup,
            )
            notified_user_ids.add(user.id)
