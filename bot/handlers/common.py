from bot.common import send_telegram_message, Chat
from users.models import User


def get_bot_user(update):
    user = User.objects.filter(telegram_id=update.effective_user.id).first()
    if not user:
        send_telegram_message(
            chat=Chat(id=update.effective_chat.id),
            text=f"😐 Извините, мы не знакомы. Привяжите свой аккаунт в профиле на https://vas3k.club"
        )
        return None

    if user.is_banned:
        send_telegram_message(
            chat=Chat(id=update.effective_user.id),
            text=f"😐 Извините, вы забанены до {user.is_banned_until.strftime('%d %B %Y')} и пока не можете писать"
        )
        return None

    return user
