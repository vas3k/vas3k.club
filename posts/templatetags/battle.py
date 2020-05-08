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
    arguments_count = len(arguments_for_a) + len(arguments_for_b)

    total_votes_a = sum(c.upvotes for c in arguments_for_a)
    total_votes_b = sum(c.upvotes for c in arguments_for_b)
    upvotes_count = total_votes_a + total_votes_b

    percent_a = 0
    percent_b = 0
    if arguments_count > 0:
        argument_percent = 100 / arguments_count
        percent_a = len(arguments_for_a) * argument_percent
        percent_b = len(arguments_for_b) * argument_percent
        if upvotes_count > 0:
            upvote_percent = 100 / upvotes_count
            percent_a = (percent_a + total_votes_a * upvote_percent) / 2
            percent_b = (percent_b + total_votes_b * upvote_percent) / 2
    return battle_stats_template.render({
        "total_arguments": {
            "a": len(arguments_for_a),
            "b": len(arguments_for_b),
        },
        "total_votes": {
            "a": total_votes_a,
            "b": total_votes_b,
        },
        "graph": {
            "percent_a": round(percent_a),
            "percent_b": round(percent_b),
        },
        "battle": post,
    })


@register.filter()
def side_name(battle, side_code):
    if battle and battle.metadata and battle.metadata.get("battle"):
        return battle.metadata["battle"]["sides"][side_code]["name"]
    return ""
