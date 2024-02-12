from collections import namedtuple

from django import template
from django.utils.safestring import mark_safe

from club import settings
from common.markdown.markdown import markdown_text

from comments.forms import BattleCommentForm

register = template.Library()

TreeComment = namedtuple("TreeComment", ["comment", "replies"])


@register.filter()
def comment_tree(comments):
    comments = list(comments)  # in case if it's a queryset
    tree = []

    # build reply tree (3 levels)
    for comment in comments:
        # find 1st level comments
        if not comment.reply_to:
            replies = []
            for reply in sorted(comments, key=lambda c: c.created_at):
                # 2nd level replies
                if reply.reply_to_id == comment.id:
                    replies.append(
                        TreeComment(
                            comment=reply,
                            replies=sorted(  # 3rd level replies
                                [c for c in comments if c.reply_to_id == reply.id],
                                key=lambda c: c.created_at
                            )
                        )
                    )
            tree.append(
                TreeComment(
                    comment=comment,
                    replies=replies
                )
            )

    # move pinned comments to the top
    tree = sorted(tree, key=lambda c: c.comment.is_pinned, reverse=True)

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
        new_html = markdown_text(comment.text)
        if new_html != comment.html:
            # to not flood into history
            comment.html = new_html
            comment.save()

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
