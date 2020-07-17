from uuid import uuid4

from slugify import slugify

from utils.strings import random_number


def generate_unique_slug(model, name, separator="-"):
    attempts = 5
    while attempts > 0:
        slug = slugify(name[:30], separator=separator)
        is_exists = model.objects.filter(slug__iexact=slug).exists()
        if not is_exists:
            return slug
        attempts -= 1
        name += random_number(length=2)
    return str(uuid4())
