from collections import defaultdict, namedtuple

from django import template
from django.utils.safestring import mark_safe

from club import settings
from comments.rate_limits import is_comment_rate_limit_exceeded
from common.markdown.markdown import markdown_text

from comments.forms import BattleCommentForm

register = template.Library()

TreeComment = namedtuple("TreeComment", ["comment", "replies"])


@register.filter()
def comment_tree(comments):
    comments = list(comments)

    children = defaultdict(list)
    for comment in comments:
        children[comment.reply_to_id].append(comment)

    for group in children.values():
        group.sort(key=lambda c: c.created_at)

    tree = []
    for comment in children.get(None, []):
        replies = [
            TreeComment(
                comment=reply,
                replies=children.get(reply.id, [])
            )
            for reply in children.get(comment.id, [])
        ]
        tree.append(TreeComment(comment=comment, replies=replies))

    tree.sort(key=lambda c: c.comment.is_pinned, reverse=True)

    return tree


@register.simple_tag(takes_context=True)
def render_comment(context, comment):
    if comment.is_deleted:
        if comment.deleted_by == comment.author_id:
            by_who = " его автором"
        elif comment.deleted_by == comment.post.author_id:
            by_who = " автором поста"
        else:
            by_who = " модератором"

        return mark_safe(
            f"""<p class="comment-text-deleted">😱 Комментарий удален{by_who}...</p>"""
        )

    if not comment.html or settings.DEBUG:
        new_html = markdown_text(comment.text, uniq_id=comment.id)
        if new_html != comment.html:
            # to not flood into history
            comment.html = new_html
            comment.save(update_fields=["html", "updated_at"])

    return mark_safe(comment.html or "")


@register.filter
def edit_form(form):
    return "comments/forms/battle.html" if isinstance(form, BattleCommentForm) else "comments/forms/comment.html"


@register.simple_tag(takes_context=True)
def selected_battle_side(context):
    try:
        return "selected" if context['comment'].battle_side == context['side']['name'] else ""
    except Exception:
        return ""

@register.filter
def is_comment_limit_exceeded(user, post):
    return is_comment_rate_limit_exceeded(post, user)
