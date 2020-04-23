from django import template

from users.models import Tag

register = template.Library()


@register.simple_tag()
def user_tag_images(user):
    tags = user.tags.filter(tag__group=Tag.GROUP_HOBBIES)[:5]
    return " ".join([str(t.name.split(" ", 1)[0]) for t in tags])
