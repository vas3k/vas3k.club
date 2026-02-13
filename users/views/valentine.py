import random

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from authn.decorators.auth import require_auth
from users.models.user import User

from telegram import Bot


PAIR_COOLDOWN_SECONDS = 60 * 60 * 24 * 365 * 10
GLOBAL_COOLDOWN_SECONDS = 60 * 30


@require_auth
@require_POST
def send_valentine(request, user_slug):
    to_user = get_object_or_404(User, slug=user_slug)

    if request.me and to_user.id == request.me.id:
        return redirect("profile", user_slug=to_user.slug)

    sender_id = request.me.id

    pair_key = f"valentine:pair:{sender_id}:{to_user.id}"
    global_key = f"valentine:cooldown:sender:{sender_id}"

    # Проверяем лимиты
    can_send = True
    if cache.get(pair_key) or cache.get(global_key):
        can_send = False

    if can_send and to_user.telegram_id:
        bot = Bot(token=settings.TELEGRAM_TOKEN)

        texts = (
            "💌 Тебе валентинка!\n\nКому-то ты правда понравился 🙂",
            "💌 Тебе валентинка!\n\nКто-то улыбнулся, глядя на твой профиль.",
            "💌 Тебе валентинка!\n\nКажется, ты кому-то симпатичен.",
        )

        text = random.choice(texts)

        try:
            bot.send_message(
                chat_id=to_user.telegram_id,
                text=text,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )

            cache.set(pair_key, True, timeout=PAIR_COOLDOWN_SECONDS)
            cache.set(global_key, True, timeout=GLOBAL_COOLDOWN_SECONDS)

        except Exception:
            pass  # намеренно игнорируем ошибки

    return render(
        request,
        "message.html",
        {
            "title": "Валентинка отправлена 💌",
            "message": (
                "Если получатель привязал клубного бота к профилю, "
                "он обязательно получит вашу валентинку 🙂"
            ),
        },
    )
