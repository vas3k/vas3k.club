import telegram

from notifications.telegram.common import Chat, CLUB_CHANNEL, send_telegram_message, render_html_message, send_telegram_image, CLUB_CHAT


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


def send_post_message(post, chat_id):
    send_telegram_message(
        chat=Chat(id=chat_id),
        text=render_html_message("channel_post_announce.html", post=post),
        parse_mode=telegram.ParseMode.HTML,
        disable_preview=True,
    )


def announce_in_club_chats(post):
    if post.topic:
        if post.topic.chat_id:
            # announce to the topic chat
            send_post_message(post, post.topic.chat_id)
        if post.topic.additional_chat_ids:
            # announce to the topic additional chats
            for additional_chat_id in post.topic.additional_chat_ids:
                send_post_message(post, additional_chat_id)
    else:
        # announce to public chat
        send_post_message(post, CLUB_CHAT)


def notify_post_author_approved(post):
    if post.author.telegram_id:
        send_telegram_message(
            chat=Chat(id=post.author.telegram_id),
            text=render_html_message("post_approved.html", post=post),
            parse_mode=telegram.ParseMode.HTML,
        )


def notify_post_author_rejected(post):
    if post.author.telegram_id:
        send_telegram_message(
            chat=Chat(id=post.author.telegram_id),
            text=render_html_message("post_rejected.html", post=post),
            parse_mode=telegram.ParseMode.HTML,
        )
