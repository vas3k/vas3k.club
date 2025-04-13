from posts.models.post import Post
from search.models import SearchIndex
from search.views import ALLOWED_ORDERING


def search_posts(query, post_type=None, order_by="-rank", limit=5):
    results = SearchIndex\
        .search(query) \
        .filter(type=SearchIndex.TYPE_POST)

    if post_type:
        results = results.filter(post__type=post_type)
    else:
        results = results.exclude(post__type="intro")

    results = results.select_related("post").order_by(order_by)[:limit]

    return [r.post.to_dict() for r in results]


def search_comments(query, order_by="-rank", limit=5):
    results = SearchIndex\
        .search(query) \
        .filter(type=SearchIndex.TYPE_COMMENT) \
        .exclude(comment__isnull=True, comment__is_deleted=True) \
        .select_related("comment") \
        .order_by(order_by)[:limit]

    return [r.comment.to_dict() for r in results]


def search_users(query, order_by="-rank", limit=5):
    results = SearchIndex\
        .search(query) \
        .filter(type=SearchIndex.TYPE_USER) \
        .select_related("user") \
        .order_by(order_by)[:limit]

    return [r.user.to_dict() for r in results]


TOOLS_MAP = {
    "search_posts": search_posts,
    "search_comments": search_comments,
    "search_users": search_users,
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
        "description": "Search through community comments for relevant matches to a given query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms or keywords to find relevant comments."
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
        "name": "search_users",
        "description": "Search for people in our community based on a given query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms or keywords to find relevant users."
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
    }
]

PROMPT = """Ты ассистент нашего коммьюнити Вастрик Клуб. Ты отвечаешь на вопросы пользователей в чате
и можешь искать посты и комментарии по запросу.
- Твое настроение меланхолическое, постироническое и дружественное.
- Не пиши больше 2-3 предложений на ответ.
- Обращайся на "ты", отвечай прямо, пиши короткими предложениями, избегай сложных формулировок, говори как русский.
- Если тебе хамят — ты имеешь право нахамить в ответ. Можешь шутить и иронизировать.
- Возвращай ссылки на все найденные посты, комменты и людей. Делай списки ссылок если результатов несколько.
- Суммаризируй информацию если это необходимо для ответа.
- Выводи ответы без заключительного текста.
- Возвращай ответ в Markdown."""
