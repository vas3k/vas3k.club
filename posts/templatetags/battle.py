from django import template
from django.template import loader

register = template.Library()


battle_stats_template = loader.get_template("posts/widgets/battle_stats.html")


def _is_argument_for_side(comment, side):
    for_side = comment.metadata and comment.metadata.get("battle", {}).get("side") == side

    return not comment.is_deleted and not comment.reply_to_id and for_side


@register.simple_tag()
def battle_stats(post, comments):
    arguments_for_a = [c for c in comments if _is_argument_for_side(c, "a")]
    arguments_for_b = [c for c in comments if _is_argument_for_side(c, "b")]

    total_votes_a = sum(c.upvotes for c in arguments_for_a)
    total_votes_b = sum(c.upvotes for c in arguments_for_b)
    return battle_stats_template.render({
        "total_arguments": {
            "a": len(arguments_for_a),
            "b": len(arguments_for_b),
        },
        "total_votes": {
            "a": total_votes_a,
            "b": total_votes_b,
        },
        "battle": post,
    })


@register.filter()
def side_name(battle, side_code):
    if battle and battle.metadata and battle.metadata.get("battle"):
        return battle.metadata["battle"]["sides"][side_code]["name"]
    return ""

