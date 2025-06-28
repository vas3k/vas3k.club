from datetime import datetime, timedelta

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, render
from django_q.tasks import async_task

from authn.decorators.auth import require_auth
from club.exceptions import AccessDenied
from common.dates import random_date_in_range
from godmode.config import ADMIN
from godmode.forms import GodmodeDigestEditForm, GodmodeInviteForm, GodmodeMassEmailForm, GodmodeMassAchievementForm
from godmode.models import ClubSettings
from invites.models import Invite
from notifications.email.custom import send_custom_mass_email
from notifications.email.invites import send_invited_email, send_account_renewed_email
from notifications.signals.achievements import async_create_or_update_achievement
from notifications.telegram.common import send_telegram_message, ADMIN_CHAT
from payments.models import Payment
from payments.products import PRODUCTS
from posts.models.post import Post
from users.models.achievements import UserAchievement
from users.models.user import User
from utils.strings import random_string


@require_auth
def godmode_digest_settings(request):
    if not request.me.is_god:
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "🥲 Вам сюда нельзя",
            "message": f"Вы не можете рассылать дайджесты, это могут делать только админы с ролью god.",
        })

    god_settings = ClubSettings.objects.first()

    if request.method == "POST":
        form = GodmodeDigestEditForm(request.POST, request.FILES, instance=god_settings)
        if form.is_valid():
            form.save()
            return redirect("godmode_settings")
    else:
        form = GodmodeDigestEditForm(instance=god_settings)

    return render(request, "godmode/simple_form.html", {
        "admin": ADMIN,
        "title": "💌 Дайджест",
        "form": form
    })


@require_auth
def godmode_invite(request):
    if not request.me.is_god:
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "🥲 Вам сюда нельзя",
            "message": f"Вы не можете приглашать людей в Клуб, это могут делать только админы с ролью god.",
        })

    if request.method == "POST":
        form = GodmodeInviteForm(request.POST, request.FILES)
        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()
            days = form.cleaned_data["days"]
            now = datetime.utcnow()

            user = User.objects.filter(email=email).first()
            if user:
                # add days to existing user instead of overwriting
                user.membership_expires_at = max(
                    now + timedelta(days=days),
                    user.membership_expires_at + timedelta(days=days)
                )
                user.membership_platform_type = User.MEMBERSHIP_PLATFORM_DIRECT
                user.updated_at = now
                user.save()
            else:
                # create new user with that email
                user, is_created = User.objects.get_or_create(
                    email=email,
                    defaults=dict(
                        membership_platform_type=User.MEMBERSHIP_PLATFORM_DIRECT,
                        full_name=email[:email.find("@")],
                        membership_started_at=now,
                        membership_expires_at=now + timedelta(days=days),
                        created_at=now,
                        updated_at=now,
                        moderation_status=User.MODERATION_STATUS_INTRO,
                    ),
                )

            if user.moderation_status == User.MODERATION_STATUS_INTRO:
                send_invited_email(request.me, user)
                send_telegram_message(
                    chat=ADMIN_CHAT,
                    text=f"🎁 <b>Юзера '{email}' заинвайтили за донат</b>",
                )
            else:
                send_account_renewed_email(request.me, user)
                send_telegram_message(
                    chat=ADMIN_CHAT,
                    text=f"🎁 <b>Юзеру '{email}' продлили аккаунт за донат</b>",
                )

            return render(request, "message.html", {
                "title": "🎁 Юзер приглашен",
                "message": f"Сейчас он получит на почту '{email}' уведомление об этом. "
                           f"Ему будет нужно залогиниться по этой почте и заполнить интро."
            })
    else:
        form = GodmodeInviteForm()

    return render(request, "godmode/simple_form.html", {
        "admin": ADMIN,
        "title": "➕ Пригласить юзера в Клуб",
        "form": form
    })


@require_auth
def godmode_generate_invite_code(request):
    if request.method != "POST":
        raise Http404()

    if not request.me.is_god:
        raise AccessDenied()

    Invite.objects.create(
        user=request.me,
        payment=Payment.create(
            reference="god-" + random_string(length=16),
            user=request.me,
            product=PRODUCTS["club1_invite"],
            status=Payment.STATUS_SUCCESS,
        )
    )

    return redirect("invites")


@require_auth
def godmode_sunday_posts(request):
    new_posts_cutoff = timedelta(days=200)
    days_range = 15
    posts = []

    while len(posts) < 20:
        random_date_in_the_past = random_date_in_range(settings.LAUNCH_DATE, datetime.utcnow() - new_posts_cutoff)
        top_old_post = Post.visible_objects() \
            .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST]) \
            .filter(is_approved_by_moderator=True) \
            .filter(
                published_at__gte=random_date_in_the_past,
                published_at__lte=random_date_in_the_past + timedelta(days=days_range)
            ) \
            .order_by("-upvotes") \
            .first()

        if top_old_post:
            posts.append(top_old_post)

    return render(request, "misc/sunday_posts.html", {
        "posts": posts
    })


@require_auth
def godmode_mass_email(request):
    if not request.me.is_god:
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "🥲 Вам сюда нельзя",
            "message": f"Вы не можете делать массовые рассылки, это могут делать только админы с ролью god.",
        })

    if request.method == "POST":
        form = GodmodeMassEmailForm(request.POST, request.FILES)
        if form.is_valid():
            emails_or_slugs = [u.strip().lstrip("@") for u in form.cleaned_data["recipients"].strip().split(",") if u.strip()]
            async_task(
                send_custom_mass_email,
                emails_or_slugs=emails_or_slugs,
                title=form.cleaned_data["email_title"],
                text=form.cleaned_data["email_text"],
                is_promo=form.cleaned_data["is_promo"],
            )
            return render(request, "message.html", {
                "title": f"📧 Рассылка запущена на {len(emails_or_slugs)} получателей",
                "message": "Вот этим людям щас будет отправлено письмо:\n" + ", ".join(emails_or_slugs)
            })
    else:
        form = GodmodeMassEmailForm()

    return render(request, "godmode/simple_form.html", {
        "admin": ADMIN,
        "title": "📤 Массовая рассылка по email и telegram юзерам",
        "form": form
    })


@require_auth
def godmode_mass_achievement(request):
    if not request.me.is_moderator:
        raise AccessDenied()

    if request.method == "POST":
        form = GodmodeMassAchievementForm(request.POST, request.FILES)
        if form.is_valid():
            slugs = form.cleaned_data["recipients"].strip().split(",")
            users = User.objects.filter(slug__in=slugs)
            for user in users:
                user_achievement, is_created = UserAchievement.objects.get_or_create(
                    user=user,
                    achievement=form.cleaned_data["achievement"],
                )
                if is_created:
                    async_create_or_update_achievement(user_achievement)

            some_user_not_found = len(slugs) != users.count()
            return render(request, "message.html", {
                "title": f"🏆 Ачивка '{form.cleaned_data['achievement'].name}' выдана {users.count()} юзерам",
                "message": "Вот эти юзеры не найдены в Клубе, возможно ошибка в нике: " + ", ".join(
                    list(set(slugs) - set([u.slug for u in users]))
                ) if some_user_not_found else "Все юзеры получили ачивки!"
            })
    else:
        form = GodmodeMassAchievementForm()

    return render(request, "godmode/simple_form.html", {
        "admin": ADMIN,
        "title": "🏆 Массовая выдача ачивок",
        "form": form
    })
