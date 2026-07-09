import re
from datetime import datetime, timedelta


SEARCH_TYPES = {"post", "comment", "user"}

CUSTOM_FILTER_RE = re.compile(
    r'(?:(?<=^)|(?<=[\s(]))(?P<operator>-author:|author:|-type:|type:|-title:|title:|since:|until:)(?P<value>"[^"]+"|[^\s()]+)',
    re.IGNORECASE,
)


def parse_search_query(query):
    parsed = {
        "query": "",
        "author": None,
        "-author": None,
        "type": None,
        "-type": None,
        "title": None,
        "-title": None,
        "since": None,
        "until": None,
    }
    if not query:
        return parsed

    def _replace_custom_filter(match):
        operator = (match.group("operator") or "").lower()
        value = (match.group("value") or "").strip('"').lower()

        if operator in {"author:", "-author:"} and value:
            parsed["-author" if operator.startswith("-") else "author"] = value
            return " "

        if operator in {"type:", "-type:"} and value in SEARCH_TYPES:
            parsed["-type" if operator.startswith("-") else "type"] = value
            return " "

        if operator in {"title:", "-title:"} and value:
            parsed["-title" if operator.startswith("-") else "title"] = value
            return " "

        if operator == "since:" and value:
            parsed["since"] = value
            return " "

        if operator == "until:" and value:
            parsed["until"] = value
            return " "

        return match.group(0)

    normalized = CUSTOM_FILTER_RE.sub(_replace_custom_filter, query)
    parsed["query"] = normalize_query_operators(normalized)
    return parsed


def normalize_query_operators(query):
    normalized = query.replace("&&", " AND ").replace("&", " AND ").replace("||", " OR ")
    normalized = re.sub(r"\b(and|or)\b", lambda m: m.group(1).upper(), normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    if not normalized:
        return ""

    # no search terms left (only operators/parentheses)
    terms_only = re.sub(r"\bAND\b|\bOR\b|[()]", " ", normalized, flags=re.IGNORECASE)
    if not terms_only.strip():
        return ""

    return normalized


def parse_date_filter_bounds(value):
    if not value:
        return None

    for fmt, step in (("%Y-%m-%d", "day"), ("%Y-%m", "month"), ("%Y", "year")):
        try:
            start = datetime.strptime(value, fmt)
        except ValueError:
            continue

        if step == "day":
            return start, start + timedelta(days=1)
        if step == "month":
            if start.month == 12:
                return start, start.replace(year=start.year + 1, month=1)
            return start, start.replace(month=start.month + 1)
        return start, start.replace(year=start.year + 1)

    return None
