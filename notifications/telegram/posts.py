import telegram
from django.conf import settings
from django.template import TemplateDoesNotExist
from django.urls import reverse

from notifications.telegram.common import Chat, CLUB_CHANNEL, send_telegram_message, render_html_message, send_telegram_image, CLUB_CHAT
from tags.models import Tag, UserTag


def announce_in_club_channel(post, announce_text=None, image=None):
    if not announce_text:
        announce_text = render_html_message("channel_post_announce.html", post=post)

    if image:
        send_telegram_image(
            chat=CLUB_CHANNEL,
            image_url=image,
            text=announce_text,
        )
    else:
        send_telegram_message(
            chat=CLUB_CHANNEL,
            text=announce_text,
            disable_preview=False,
            parse_mode=telegram.ParseMode.HTML,
        )


def announce_in_club_chats(post):
    post_url = settings.APP_HOST + reverse("show_post", kwargs={
        "post_type": post.type,
        "post_slug": post.slug
    })
    post_reply_markup = telegram.InlineKeyboardMarkup([
        [
            telegram.InlineKeyboardButton("👍", callback_data=f"upvote_post:{post.id}"),
            telegram.InlineKeyboardButton("🔗", url=post_url),
            telegram.InlineKeyboardButton("🔔", callback_data=f"subscribe:{post.id}"),
        ],
    ])

    # announce to public chat
    if post.is_visible_in_feeds or not post.room or not post.room.chat_id:
        send_telegram_message(
            chat=CLUB_CHAT,
            text=render_html_message("channel_post_announce.html", post=post),
            parse_mode=telegram.ParseMode.HTML,
            disable_preview=True,
            reply_markup=post_reply_markup,
        )

    if post.room and post.room.chat_id and post.room.send_new_posts_to_chat:
        # announce to the room chat
        send_telegram_message(
            chat=Chat(id=post.room.chat_id),
            text=render_html_message("channel_post_announce.html", post=post),
            parse_mode=telegram.ParseMode.HTML,
            disable_preview=True,
            reply_markup=post_reply_markup,
        )


def notify_post_approved(post):
    if post.author.telegram_id:
        send_telegram_message(
            chat=Chat(id=post.author.telegram_id),
            text=render_html_message("post_approved.html", post=post),
            parse_mode=telegram.ParseMode.HTML,
        )


def notify_post_rejected(post, reason):
    try:
        text = render_html_message(f"post_rejected/{reason.value}.html", post=post)
    except TemplateDoesNotExist:
        text = render_html_message(f"post_rejected/draft.html", post=post)

    if post.author.telegram_id:
        send_telegram_message(
            chat=Chat(id=post.author.telegram_id),
            text=text,
            parse_mode=telegram.ParseMode.HTML,
        )


def notify_post_collectible_tag_owners(post):
    if post.collectible_tag_code:
        tag = Tag.objects.filter(code=post.collectible_tag_code, group=Tag.GROUP_COLLECTIBLE).first()
        if tag:
            tag_users = UserTag.objects.filter(tag=tag).select_related("user").all()
            for tag_user in tag_users:
                if tag_user.user.telegram_id:
                    send_telegram_message(
                        chat=Chat(id=tag_user.user.telegram_id),
                        text=render_html_message("post_collectible_tag.html", post=post, tag=tag),
                        parse_mode=telegram.ParseMode.HTML,
                    )
