import telegram
from django.conf import settings
from django.template import TemplateDoesNotExist
from django.urls import reverse

from common.regexp import USERNAME_RE
from notifications.telegram.common import Chat, CLUB_CHANNEL, send_telegram_message, render_html_message, \
    send_telegram_image, CLUB_CHAT, ADMIN_CHAT, CLUB_ONLINE, VIBES_CHAT
from posts.models.post import Post
from rooms.models import RoomSubscription
from tags.models import Tag, UserTag
from users.models.friends import Friend
from users.models.user import User

REJECT_POST_REASONS = {
    "post": [
        ("title", "Плохой заголовок"),
        ("design", "Текст недооформлен"),
        ("value", "Нет пользы/абстрактно"),
        ("inside", "Нет инсайдов и опыта"),
    ],
    "event": [
        ("title", "Плохой заголовок"),
        ("design", "Текст недооформлен"),
    ],
    "guide": [
        ("title", "Плохой заголовок"),
        ("design", "Текст недооформлен"),
    ],
    "thread": [
        ("title", "Плохой заголовок"),
        ("design", "Текст недооформлен"),
        ("duplicate", "Дубликат"),
    ],
    "question": [
        ("title", "Плохой заголовок"),
        ("dyor", "Нет рисёрча, коротко"),
        ("hot", "Провокация/срач"),
        ("chat", "Лучше в чат"),
        ("duplicate", "Дубликат"),
    ],
    "link": [
        ("tldr", "Короткое описание"),
        ("self", "Ссылка на себя"),
        ("value", "Бесполезно/непонятно"),
    ],
    "idea": [
        ("title", "Плохой заголовок"),
        ("tldr", "Мало описания"),
        ("github", "Фича, на гитхаб"),
    ],
    "battle": [
        ("hot", "Срач"),
        ("false_dilemma", "Ложная дилемма"),
        ("duplicate", "Дубликат"),
        ("bias", "Предвзят к одному варианту"),
    ],
    "project": [
        ("ad", "Похоже на рекламу"),
        ("inside", "Нет инсайдов и опыта"),
    ],
}


def send_published_post_to_moderators(post):
    send_telegram_message(
        chat=ADMIN_CHAT,
        text=render_html_message("moderator_new_post_review.html", post=post),
        reply_markup=telegram.InlineKeyboardMarkup([
            *[
                [telegram.InlineKeyboardButton(f"❌ {title}", callback_data=f"reject_post_{reason}:{post.id}")]
                for reason, title in REJECT_POST_REASONS.get(post.type) or []
            ],
            [
                telegram.InlineKeyboardButton("❌ В черновики", callback_data=f"reject_post:{post.id}"),
                telegram.InlineKeyboardButton("😕 Так себе", callback_data=f"forgive_post:{post.id}"),
            ],
            [
                telegram.InlineKeyboardButton("👍 Одобрить", callback_data=f"approve_post:{post.id}"),
            ],
        ])
    )


def send_intro_changes_to_moderators(post):
    if post.type == Post.TYPE_INTRO:
        send_telegram_message(
            chat=ADMIN_CHAT,
            text=render_html_message("moderator_updated_intro.html", user=post.author, intro=post),
        )


def announce_in_online_channel(post):
    send_telegram_message(
        chat=CLUB_ONLINE,
        text=render_html_message("channel_post_announce.html", post=post),
        parse_mode=telegram.ParseMode.HTML,
        disable_preview=True,
    )


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
    # announce to public chat
    if post.visibility == Post.VISIBILITY_EVERYWHERE or not post.room or not post.room.chat_id:
        send_telegram_message(
            chat=CLUB_CHAT,
            text=render_html_message("channel_post_announce.html", post=post),
            parse_mode=telegram.ParseMode.HTML,
            disable_preview=True,
            reply_markup=post_reply_markup(post),
        )

    if post.room and post.room.chat_id and post.room.send_new_posts_to_chat:
        # announce to the room chat
        send_telegram_message(
            chat=Chat(id=post.room.chat_id),
            text=render_html_message("channel_post_announce.html", post=post),
            parse_mode=telegram.ParseMode.HTML,
            disable_preview=True,
            reply_markup=post_reply_markup(post),
        )


def notify_post_approved(post: Post):
    if not post.author.telegram_id:
        return None

    if post.room_id and post.is_room_only:
        send_telegram_message(
            chat=Chat(id=post.author.telegram_id),
            text=render_html_message("post_approved_in_room.html", post=post),
            parse_mode=telegram.ParseMode.HTML,
        )
    else:
        send_telegram_message(
            chat=Chat(id=post.author.telegram_id),
            text=render_html_message("post_approved.html", post=post),
            parse_mode=telegram.ParseMode.HTML,
        )

    return None


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
                        reply_markup=post_reply_markup(post),
                    )

def notify_author_friends(post):
    notified_user_ids = set()

    # parse @nicknames and notify mentioned users
    for username in USERNAME_RE.findall(post.text):
        user = User.objects.filter(slug=username).first()
        if user and user.telegram_id and user.id not in notified_user_ids:
            send_telegram_message(
                chat=Chat(id=user.telegram_id),
                text=render_html_message("post_mention.html", post=post),
            )
            notified_user_ids.add(user.id)

    # notify friends about new posts
    friends = Friend.friends_for_user(post.author)
    for friend in friends:
        if friend.user_from.telegram_id \
            and friend.is_subscribed_to_posts \
            and friend.user_from.id not in notified_user_ids:
            send_telegram_message(
                chat=Chat(id=friend.user_from.telegram_id),
                text=render_html_message("friend_post.html", post=post),
            )
            notified_user_ids.add(friend.user_from.id)


def notify_post_room_subscribers(post):
    if post.room:
        subscribers = RoomSubscription.room_subscribers(post.room)
        for subscriber in subscribers:
            if subscriber.user.telegram_id:
                send_telegram_message(
                    chat=Chat(id=subscriber.user.telegram_id),
                    text=render_html_message("post_room_subscriber.html", post=post, room=post.room),
                    parse_mode=telegram.ParseMode.HTML,
                    reply_markup=post_reply_markup(post),
                )


def post_reply_markup(post):
    post_url = settings.APP_HOST + reverse("show_post", kwargs={
        "post_type": post.type,
        "post_slug": post.slug
    })

    return telegram.InlineKeyboardMarkup([
        [
            telegram.InlineKeyboardButton("👍", callback_data=f"upvote_post:{post.id}"),
            telegram.InlineKeyboardButton("🔗", url=post_url),
            telegram.InlineKeyboardButton("🔔", callback_data=f"subscribe:{post.id}"),
        ],
    ])


def notify_post_label_changed(post):
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


def notify_admins_on_post_label_changed(post):
    for chat in [ADMIN_CHAT, VIBES_CHAT]:
        send_telegram_message(
            chat=chat,
            text=f"🏷️ Посту «{post.title}» выдан лейбл «{post.label_code}»"
        )


def notify_post_coauthors_changed(post):
    old = set()
    history = list(post.history.all()[:2])
    if len(history) == 2:
        old = set(history[1].coauthors)
    new = set(post.coauthors)
    added = new - old
    removed = old - new
    notify_users_by_username(added, "coauthor_added.html", post)
    notify_users_by_username(removed, "coauthor_removed.html", post)


def notify_users_by_username(users, template, post):
    for username in users:
        user = User.objects.filter(slug=username).first()
        if user and user.telegram_id:
            send_telegram_message(
                chat=Chat(id=user.telegram_id),
                text=render_html_message(template, post=post),
            )
