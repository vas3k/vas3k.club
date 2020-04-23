from collections import namedtuple

from django import template
from django.utils.safestring import mark_safe

from club import settings
from common.markdown.markdown import markdown_text

register = template.Library()

TreeComment = namedtuple("TreeComment", ["comment", "replies"])


@register.filter()
def comment_tree(comments, ordering="top"):
    comments = list(comments)  # in case if it's a queryset
    tree = []

    for comment in comments:
        if not comment.reply_to:
            # take the high level comment and find all replies for it
            tree_comment = TreeComment(
                comment=comment,
                replies=[c for c in comments if c.reply_to_id == comment.id],
            )
            tree.append(tree_comment)

    if ordering == "top":
        # sort by number of upvotes
        tree = sorted(tree, key=lambda c: c.comment.upvotes, reverse=True)

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
