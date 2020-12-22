from django import template
from django.conf import settings
from django.template import loader
from django.template.defaultfilters import truncatechars
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

from common.embeds import CUSTOM_ICONS, CUSTOM_PARSERS
from common.regexp import FAVICON_RE
from common.markdown.markdown import markdown_text, markdown_plain
from posts.helpers import extract_any_image
from posts.models.post import Post

register = template.Library()


@register.simple_tag(takes_context=True)
def css_classes(context, post):
    classes = [f"feed-post-{post.type}"]
    me = context.get("me")

    if me and hasattr(post, "unread_comments") and post.unread_comments:
        classes += ["feed-post-is-new"]

    # if post.is_pinned:
    #     classes += ["feed-post-is-pinned"]

    return " ".join(classes)


@register.simple_tag(takes_context=True)
def render_post(context, post):
    if post.type == Post.TYPE_WEEKLY_DIGEST:
        # never render digests again to preserve their original state
        return post.html

    if not post.html or settings.DEBUG:
        new_html = markdown_text(post.text)
        if new_html != post.html:
            # to not flood into history
            post.html = new_html
            post.save()

    return mark_safe(post.html or "")


@register.simple_tag(takes_context=True)
def render_plain(context, post, truncate=None):
    result = mark_safe(strip_tags(markdown_plain(post.text)))
    if truncate:
        result = truncatechars(result, truncate)
    return result


@register.simple_tag()
def link_icon(post):
    if post.metadata:
        if post.metadata.get("domain") in CUSTOM_ICONS:
            icon = CUSTOM_ICONS[post.metadata["domain"]]
            return mark_safe(f"""<span class="link-favicon">{icon}</span>""")

    if post.image and FAVICON_RE.match(post.image):
        return mark_safe(f"""<span class="link-favicon" style="background-image: url('{post.image}');"></span>""")

    return mark_safe("""<span class="link-favicon"><i class="fas fa-link"></i></span>""")


summary_template = loader.get_template("posts/embeds/summary.html")


@register.simple_tag()
def link_summary(post):
    if not post.metadata or not post.metadata.get("title") or not post.metadata.get("url"):
        return ""

    embed = ""
    if post.metadata.get("domain") in CUSTOM_PARSERS:
        parser = CUSTOM_PARSERS[post.metadata["domain"]]
        if parser.get("do_not_parse"):
            return ""
        embed = parser["template"].render(parser["data"](post))

    return summary_template.render({
        "post": post,
        "embed": mark_safe(embed)
    })


@register.filter
def can_upvote(user, post_or_comment):
    return bool(user and user != post_or_comment.author)


@register.filter
def any_image(post, default="/static/images/share.png"):
    return extract_any_image(post) or default
