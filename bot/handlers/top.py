from datetime import timedelta, datetime

from django.conf import settings
from django.db.models import Q
from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from bot.decorators import is_club_member
from comments.models import Comment
from notifications.telegram.common import render_html_message
from posts.models.post import Post

TOP_TIMEDELTA = timedelta(days=3)


@is_club_member
def command_top(update: Update, context: CallbackContext) -> None:
    # Top posts
    top_posts = Post.visible_objects()\
        .filter(published_at__gte=datetime.utcnow() - TOP_TIMEDELTA)\
        .filter(Q(is_approved_by_moderator=True) | Q(upvotes__gte=settings.COMMUNITY_APPROVE_UPVOTES)) \
         .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST])\
        .order_by("-upvotes")[:5]

    # Hot posts
    hot_posts = Post.visible_objects()\
        .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST]) \
        .exclude(id__in=[p.id for p in top_posts]) \
        .order_by("-hotness")[:3]

    # Top intros
    top_intros = Post.visible_objects()\
        .filter(type=Post.TYPE_INTRO, published_at__gte=datetime.utcnow() - TOP_TIMEDELTA)\
        .select_related("author")\
        .order_by("-upvotes")[:3]

    # Top comments
    top_comment = Comment.visible_objects() \
        .filter(created_at__gte=datetime.utcnow() - TOP_TIMEDELTA) \
        .filter(is_deleted=False)\
        .exclude(post__type=Post.TYPE_BATTLE) \
        .select_related("author") \
        .order_by("-upvotes") \
        .first()

    update.effective_chat.send_message(
        render_html_message(
            template="top.html",
            top_posts=top_posts,
            hot_posts=hot_posts,
            top_intros=top_intros,
            top_comment=top_comment,
        ),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )
