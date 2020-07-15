import telegram
from django.conf import settings
from django.urls import reverse

from bot.common import Chat, ADMIN_CHAT, send_telegram_message, render_html_message


def notify_profile_needs_review(user, intro):
    user_profile_url = settings.APP_HOST + reverse("profile", kwargs={"user_slug": user.slug})
    send_telegram_message(
        chat=ADMIN_CHAT,
        text=render_html_message("moderator_new_member_review.html", user=user, intro=intro),
        reply_markup=telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton("👍 Впустить", callback_data=f"approve_user:{user.id}"),
                telegram.InlineKeyboardButton("❌️ Отказать", callback_data=f"reject_user:{user.id}"),
            ],
            [
                telegram.InlineKeyboardButton("😏 Посмотреть", url=user_profile_url),
            ]
        ])
    )


def notify_user_profile_approved(user):
    user_profile_url = settings.APP_HOST + reverse("profile", kwargs={"user_slug": user.slug})

    if user.telegram_id:
        send_telegram_message(
            chat=Chat(id=user.telegram_id),
            text=f"🚀 Подравляем! Вы прошли модерацию. Добро пожаловать в Клуб!"
                 f"\n\nМожно пойти заполнить другие смешные поля в профиле:"
                 f"\n\n{user_profile_url}"
        )


def notify_user_profile_rejected(user):
    user_profile_url = settings.APP_HOST + reverse("profile", kwargs={"user_slug": user.slug})

    if user.telegram_id:
        send_telegram_message(
            chat=Chat(id=user.telegram_id),
            text=f"😐 К сожалению, ваш профиль не прошел модерацию. Вот популярные причины почему так бывает:\n\n"
                 f"- 📝 Маленькое #intro. Допишите еще хотя бы пару абзацев. Для примера посмотрите чужие, "
                 f"там есть ссылочки. <a href=\"https://vas3k.club/docs/about/#rules\">Наши правила</a>, "
                 f"с которыми вы согласились, запрещают анонимусов в Клубе.\n"
                 f"- 🤔 Много незаполненных полей. Мы не поняли кто вы. Профиль без фамилии или компании вряд "
                 f"ли пройдет модерацию.\n"
                 f"- 🤪 Вымышленное имя или профессия (например, Олег).\n"
                 f"- 🙅‍♀️ Наличие фраз типа «не скажу», «не люблю писать о себе», «потом заполню». "
                 f"Потом так потом, мы не торопимся :)\n"
                 f"- 💨 Душность, глупость или желание обмануть модераторов.\n\n"
                 f"\n\nВот ссылка чтобы исправить недочёты и податься на ревью еще раз: {user_profile_url}"
        )


def notify_user_ping(user, message):
    if user.telegram_id:
        send_telegram_message(
            chat=Chat(id=user.telegram_id),
            text=f"👋 <b>Вам письмо от модераторов Клуба:</b> {message}"
        )
