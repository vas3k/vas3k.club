import random

from django import template
from django.utils.safestring import mark_safe

from common.data.greetings import DUMB_GREETINGS
from common.markdown.markdown import markdown_email

register = template.Library()


@register.filter(is_safe=True)
def email_markdown(text):
    return mark_safe(markdown_email(text))


@register.simple_tag(takes_context=True)
def render_email(context, post_or_comment):
    return mark_safe(markdown_email(post_or_comment.text))


@register.simple_tag()
def random_greeting():
    return random.choice(DUMB_GREETINGS)
