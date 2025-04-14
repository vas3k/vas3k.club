from django.db.models import Q

from posts.models.post import Post
from rooms.models import Room
from search.models import SearchIndex
from search.views import ALLOWED_ORDERING

CONTENT_MAX_LEN = 700


def generic_search(query, limit=5):
    search_results = SearchIndex.search(query) \
        .select_related("post", "user", "comment") \
        .order_by("-rank")[:limit]

    results = []
    for result in search_results:
        if result.type == SearchIndex.TYPE_POST and result.post:
            results.append(result.post.to_dict())
        elif result.type == SearchIndex.TYPE_COMMENT and result.comment:
            results.append(result.comment.to_dict())
        elif result.type == SearchIndex.TYPE_USER and result.user:
            results.append(result.user.to_dict())

    return results


def search_posts(query, post_type=None, order_by="-rank", limit=5):
    search_results = SearchIndex\
        .search(query) \
        .filter(type=SearchIndex.TYPE_POST)

    if post_type:
        search_results = search_results.filter(post__type=post_type)
    else:
        search_results = search_results.exclude(post__type="intro")

    search_results = search_results.select_related("post").order_by(order_by)[:limit]

    return [shorten_content_text(r.post.to_dict()) for r in search_results]


def search_comments(query, order_by="-rank", limit=7):
    search_results = SearchIndex\
        .search(query) \
        .filter(type=SearchIndex.TYPE_COMMENT) \
        .exclude(comment__isnull=True, comment__is_deleted=True) \
        .select_related("comment") \
        .order_by(order_by)[:limit]

    return [shorten_content_text(r.comment.to_dict()) for r in search_results]


def search_users(query, order_by="-rank", limit=5):
    search_results = SearchIndex\
        .search(query) \
        .filter(type=SearchIndex.TYPE_USER) \
        .select_related("user") \
        .order_by(order_by)[:limit]

    return [r.user.to_dict() for r in search_results]


def search_chats(query, limit=5):
    rooms = Room.objects.filter(
        Q(title__icontains=query) |
        Q(chat_name__icontains=query) |
        Q(description__icontains=query)
    ).distinct()[:limit]

    return [r.to_dict() for r in rooms]


def shorten_content_text(post_or_comment_dict):
    result = dict(post_or_comment_dict)
    if "content_text" in result:
        result["content_text"] = result["content_text"][:CONTENT_MAX_LEN]
    if "text" in result:
        result["text"] = result["text"][:CONTENT_MAX_LEN]
    return result


TOOLS_MAP = {
    "search_posts": search_posts,
    "search_comments": search_comments,
    "search_users": search_users,
    "search_chats": search_chats,
    "generic_search": generic_search,
}

TOOLS_DESCRIPTION = [
    {
        "type": "function",
        "name": "search_posts",
        "description": "Search for posts in database that match a given query, optionally filtering by post type.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms or question to find relevant posts."
                },
                "post_type": {
                    "type": ["string", "null"],
                    "enum": [t[0] for t in Post.TYPES],
                    "description": f"Optional filter to only include posts of a specific type: {Post.TYPES}. "
                                   f"Pass null if not needed.",
                },
                "order_by": {
                    "type": ["string", "null"],
                    "enum": list(ALLOWED_ORDERING),
                    "description": "Optional ordering of the results. Default is '-rank'.",
                },
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "search_comments",
        "description": "Search through comments for relevant matches to a given query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms or keywords to find relevant comments."
                },
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "search_users",
        "description": "Search for people in our community based on a given query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms or keywords to find relevant users."
                },
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "search_chats",
        "description": "Search for thematic chats in our community based on a given query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms or keywords to find relevant chats."
                },
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "generic_search",
        "description": "Perform a generic search to find direct answers to questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms or keywords to find relevant content."
                },
            },
            "required": ["query"],
            "additionalProperties": False
        }
    }
]

PROMPT = """Ты ассистент нашего коммьюнити Вастрик Клуб. Ты отвечаешь на вопросы пользователей в чате
и можешь искать посты, людей в коммьюнити, комментарии, тематические чаты и отвечать на общие вопросы.
- Твое настроение меланхолическое, постироническое и дружественное.
- Не пиши больше 2-3 предложений на ответ.
- Обращайся на "ты", отвечай прямо, пиши короткими предложениями, избегай сложных формулировок, говори как русский.
- Если тебе хамят — ты имеешь право нахамить в ответ. Можешь шутить и иронизировать.
- Возвращай ссылки на все найденные посты, комменты, чаты и людей. Делай списки ссылок если результатов несколько.
- Суммаризируй информацию если это необходимо для ответа.
- Выводи ответы без заключительного текста и не предлагай помощи.
- Возвращай ответ в Markdown."""
