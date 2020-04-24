from django import template
from django.template import loader

register = template.Library()


battle_stats_template = loader.get_template("posts/widgets/battle_stats.html")


@register.simple_tag()
def battle_stats(post, comments):
    total_arguments_a = len([
        c.id for c in comments
        if not c.reply_to_id and c.metadata and c.metadata.get("battle", {}).get("side") == "a"
    ])
    total_arguments_b = len([
        c.id for c in comments
        if not c.reply_to_id and c.metadata and c.metadata.get("battle", {}).get("side") == "b"
    ])

    return battle_stats_template.render({
        "total_arguments": {
            "a": total_arguments_a,
            "b": total_arguments_b,
        },
        "post": post,
    })
