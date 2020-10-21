import json
from collections import namedtuple

from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

from posts.templatetags.text_filters import cool_date
from club import settings
from common.markdown.markdown import markdown_text

register = template.Library()

TreeComment = namedtuple("TreeComment", ["comment", "replies"])


@register.filter()
def comment_tree(comments):
    comments = list(comments)  # in case if it's a queryset
    tree = []

    for comment in comments:
        if not comment.reply_to:
            # take the high level comment and find all replies for it
            tree_comment = TreeComment(
                comment=comment,
                replies=sorted(
                    [c for c in comments if c.reply_to_id == comment.id],
                    key=lambda c: c.created_at
                ),
            )
            tree.append(tree_comment)

    # move pinned comments to the top
    tree = sorted(tree, key=lambda c: c.comment.is_pinned, reverse=True)

    return tree

@register.simple_tag()
def comment_data(comment, user):
    return json.dumps({
        "url": reverse("show_post", args=[comment.post.type, comment.post.slug]),
        "createdAt": cool_date(comment.created_at),
        "author": {
            "fullName": comment.author.full_name,
            "slug": comment.author.slug,
            "profileUrl": reverse("profile", args=[comment.author.slug]),
            "position": comment.author.position,
            "avatar": comment.author.get_avatar(),
            "hat": comment.author.hat
        },
        "upvote": {
            "count": comment.upvotes,
            "hoursToRetract":settings.RETRACT_VOTE_IN_HOURS,
            "upvoteUrl": reverse("upvote_comment", args=[comment.id]),
            "retractVoteUrl": reverse("retract_comment_vote", args=[comment.id]),
            "isVoted": True if comment.is_voted else False,
            "upvotedAt" : comment.upvoted_at,
            "isDisabled": not bool(user and user != comment.author)
        }
    })

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
