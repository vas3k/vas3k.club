def calculate_similarity(my, theirs, tags):
    similarity = {}
    for group in ('personal', 'hobbies'):
        all_names = {tag.code for tag in tags if tag.group == group}
        my_names = all_names & my
        their_names = all_names & theirs
        both = my_names | their_names
        same = my_names & their_names
        similarity[group] = len(same) * 100 / len(both) if both else 0
    return similarity


def is_role_manageable_by_user(role, user):
    if role in (user.ROLE_GOD, user.ROLE_MODERATOR):
        return user.is_god
    if role == user.ROLE_CURATOR:
        return user.is_moderator
    return False
