from datetime import timedelta, datetime

from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from comments.models import Comment
from notifications.telegram.common import render_html_message
from posts.models.post import Post

TOP_TIMEDELTA = timedelta(days=3)


def command_top(update: Update, context: CallbackContext) -> None:
    # Top posts
    top_posts = Post.visible_objects()\
        .filter(is_approved_by_moderator=True, published_at__gte=datetime.utcnow() - TOP_TIMEDELTA)\
        .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST])\
        .order_by("-upvotes")[:7]

    # Top intros
    top_intros = Post.visible_objects()\
        .filter(type=Post.TYPE_INTRO, published_at__gte=datetime.utcnow() - TOP_TIMEDELTA)\
        .order_by("-upvotes")[:3]

    # Top comments
    top_comments = Comment.visible_objects() \
        .filter(created_at__gte=datetime.utcnow() - TOP_TIMEDELTA) \
        .filter(is_deleted=False)\
        .exclude(post__type=Post.TYPE_BATTLE)\
        .order_by("-upvotes")[:3]

    update.effective_chat.send_message(
        render_html_message(
            template="top.html",
            top_posts=top_posts,
            top_intros=top_intros,
            top_comments=top_comments
        ),
        parse_mode=ParseMode.HTML
    )
