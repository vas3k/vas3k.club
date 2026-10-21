from django.http import Http404, HttpResponse
from django.shortcuts import render, get_object_or_404

from club.exceptions import NotFound

from notifications.digests import generate_weekly_digest
from notifications.helpers import verify_notification_token
from users.models.user import User


def email_confirm(request, user_id, secret):
    user = get_object_or_404(User, id=user_id, deleted_at__isnull=True)
    if not verify_notification_token(user, secret):
        raise Http404()
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])

    return render(request, "message.html", {
        "title": "💌 Ваш адрес почты подтвержден",
        "message": "Теперь туда будет приходить еженедельный журнал Клуба и другие оповещалки."
    })


def email_unsubscribe(request, user_id, secret):
    user = get_object_or_404(User, id=user_id, deleted_at__isnull=True)
    if not verify_notification_token(user, secret):
        raise Http404()

    user.is_email_unsubscribed = True
    user.email_digest_type = User.EMAIL_DIGEST_TYPE_NOPE
    user.save(update_fields=["is_email_unsubscribed", "email_digest_type"])

    return render(request, "message.html", {
        "title": "🙅‍♀️ Вы отписались от всех писем Клуба",
        "message": "Мы ценим ваше время, потому отписали вас от всего и полностью. "
                   "Вы больше не получите от нас никаких писем. "
                   "Если захотите подписаться заново — напишите нам в поддержку."
    })


def email_digest_switch(request, digest_type, user_id, secret):
    user = get_object_or_404(User, id=user_id, deleted_at__isnull=True)
    if not verify_notification_token(user, secret):
        raise Http404()

    if not dict(User.EMAIL_DIGEST_TYPES).get(digest_type):
        raise Http404()

    user.email_digest_type = digest_type
    user.is_email_unsubscribed = False
    user.save(update_fields=["email_digest_type", "is_email_unsubscribed"])

    if digest_type == User.EMAIL_DIGEST_TYPE_DAILY:
        return render(request, "message.html", {
            "title": "🔥 Теперь вы будете получать дейли-дайджест",
            "message": "Офигенно. "
                       "Теперь каждое утро вам будет приходить ваша персональная подборка всего нового в Клубе."
        })
    elif digest_type == User.EMAIL_DIGEST_TYPE_WEEKLY:
        return render(request, "message.html", {
            "title": "📅 Теперь вы получаете только еженедельный журнал",
            "message": "Раз в неделю вам будет приходить подборка лучшего контента в Клубе за эту неделю, "
                       "а также важные новости, вроде изменения правил. "
                       "Это удобно, качественно и не отнимает ваше время."
        })
    elif digest_type == User.EMAIL_DIGEST_TYPE_NOPE:
        return render(request, "message.html", {
            "title": "🙅‍♀️ Вы отписались от рассылок Клуба",
            "message": "Мы ценим ваше время, потому отписали вас от наших рассылок контента. "
                       "Можете следить за новыми постами в телеграме или через бота."
        })
    else:
        return render(request, "message.html", {
            "title": "👍 Данные подписки изменены",
            "message": ""
        })


def render_weekly_digest(request):
    try:
        digest, _ = generate_weekly_digest(no_footer=True)
    except NotFound:
        raise Http404()

    return HttpResponse(digest)
