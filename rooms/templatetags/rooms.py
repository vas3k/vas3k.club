import re

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from rooms.models import RoomSubscription, RoomMuted

register = template.Library()


FLAG_EMOJI_RE = re.compile(r"[\U0001F1E6-\U0001F1FF]{2}")

@register.filter
def is_room_subscribed(room, user):
    if not user or not room:
        return False
    return RoomSubscription.is_subscribed(user, room)


@register.filter
def is_room_muted(room, user):
    if not user or not room:
        return False
    return RoomMuted.is_muted(user, room)


@register.filter
def network_icon(icon):
    if not icon:
        return ""

    flag_count = len(FLAG_EMOJI_RE.findall(icon))

    def replace_flag(match):
        flag = match.group(0)
        codepoints = "-".join(format(ord(char), "x") for char in flag)
        return format_html(
            '<img class="emoji-flag" src="https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/{}.svg" alt="{}" loading="lazy">',
            codepoints,
            flag,
        )

    rendered_icon = FLAG_EMOJI_RE.sub(lambda match: str(replace_flag(match)), icon)
    if flag_count > 1:
        rendered_icon = re.sub(r"<br\s*/?>", "", rendered_icon, flags=re.IGNORECASE)
        rendered_icon = re.sub(
            r'(loading="lazy">)\s+(<img class="emoji-flag")',
            r"\1\2",
            rendered_icon,
        )
        return format_html(
            '<span class="emoji-flags emoji-flags-multiple">{}</span>',
            mark_safe(rendered_icon),
        )
    return mark_safe(rendered_icon)
