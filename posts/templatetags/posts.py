from urllib.parse import urlencode

from django import template
from django.conf import settings
from django.template import loader
from django.template.defaultfilters import truncatechars
from django.urls import reverse
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
def feed_ordering_url(topic, label_code, post_type, ordering_type):
    if topic:
        return reverse("feed_topic_ordering", args=[topic.slug, ordering_type])
    elif label_code:
        return reverse("feed_label_ordering", args=[label_code, ordering_type])
    else:
        return reverse("feed_ordering", args=[post_type, ordering_type])


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
    if not post.metadata or not any(map(post.metadata.get, ['title', 'url', 'description'])):
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
def any_image(post):
    return extract_any_image(post) or settings.OG_IMAGE_DEFAULT


@register.simple_tag()
def og_image(post):
    if not settings.OG_IMAGE_GENERATOR_URL:
        return any_image(post)

    params = urlencode({
        **settings.OG_IMAGE_GENERATOR_DEFAULTS,
        "title": f"{post.prefix} {post.title}" if post.prefix else post.title,
        "author": post.author.slug,
        "ava": post.author.get_avatar(),
        "bg": extract_any_image(post) or "#FFFFFF"
    })

    return f"{settings.OG_IMAGE_GENERATOR_URL}?{params}"
