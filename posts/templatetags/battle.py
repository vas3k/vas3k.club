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
        "graph": graph_percentages(len(arguments_for_a), len(arguments_for_b), total_votes_a, total_votes_b),
        "battle": post,
    })


@register.filter()
def side_name(battle, side_code):
    if battle and battle.metadata and battle.metadata.get("battle"):
        return battle.metadata["battle"]["sides"][side_code]["name"]
    return ""


def graph_percentages(a_arguments: int, b_arguments: int, a_votes: int, b_votes: int):
    """Counts percentages for battle graph

    Percentage for a side is a rounded up arithmetic average of side's argument and upvote percentages

    For each side: (argument % of total arguments amount + vote % of total votes amount ) / 2
    """
    percent_a = 0
    percent_b = 0
    total_arguments = a_arguments + b_arguments
    total_upvotes = a_votes + b_votes
    if total_arguments > 0:
        argument_percent = 100 / total_arguments
        percent_a = a_arguments * argument_percent
        percent_b = b_arguments * argument_percent
        if total_upvotes > 0:
            upvote_percent = 100 / total_upvotes
            percent_a = (percent_a + a_votes * upvote_percent) / 2
            percent_b = (percent_b + b_votes * upvote_percent) / 2
    return {
        "percent_a": round(percent_a),
        "percent_b": round(percent_b)
    }
