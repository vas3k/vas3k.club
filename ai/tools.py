from django.db.models import Q

from ai.config import TRIM_LONG_CONTENT_TO_LEN, CLUB_INFO_POST_SLUGS, CLUB_INFO_POST_LABEL
from posts.models.post import Post
from rooms.models import Room
from search.models import SearchIndex
from search.views import ALLOWED_ORDERING
from users.models.user import User


def generic_search(query, limit=5):
    search_results = SearchIndex.search(query) \
        .select_related("post", "user", "comment") \
        .order_by("-rank")[:limit]

    results = []
    for result in search_results:
        if result.type == SearchIndex.TYPE_POST and result.post:
            results.append(result.post.to_dict(including_private=True))
        elif result.type == SearchIndex.TYPE_COMMENT and result.comment:
            results.append(result.comment.to_dict())
        elif result.type == SearchIndex.TYPE_USER and result.user:
            if result.user.profile_publicity_level != User.PUBLICITY_LEVEL_PRIVATE:
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

    return [shorten_content_text(r.post.to_dict(including_private=True)) for r in search_results]


def search_comments(query, order_by="-rank", limit=7):
    search_results = SearchIndex\
        .search(query) \
        .filter(type=SearchIndex.TYPE_COMMENT) \
        .exclude(comment__isnull=True, comment__is_deleted=True) \
        .select_related("comment") \
        .order_by(order_by)[:limit]

    return [shorten_content_text(r.comment.to_dict()) for r in search_results]


def search_users(query, order_by="-rank", limit=7):
    search_results = SearchIndex\
        .search(query) \
        .filter(type=SearchIndex.TYPE_USER) \
        .exclude(user__isnull=True, user__deleted_at__isnull=True) \
        .exclude(user__profile_publicity_level=User.PUBLICITY_LEVEL_PRIVATE) \
        .filter(user__moderation_status=User.MODERATION_STATUS_APPROVED) \
        .select_related("user") \
        .order_by(order_by)[:limit]

    intros = {}
    if search_results:
        intros = dict(Post.visible_objects().filter(
            type=Post.TYPE_INTRO,
            author_id__in=[s.user_id for s in search_results if s.user_id]
        ).values_list("author_id", "text"))

    return [{
        **r.user.to_dict(),
        "intro": (intros.get(r.user_id) or "")[:TRIM_LONG_CONTENT_TO_LEN],
    } for r in search_results if r.user_id]


def search_chats(query, limit=30):
    rooms = Room.objects.filter(
        Q(title__icontains=query) |
        Q(chat_name__icontains=query) |
        Q(description__icontains=query)
    ).distinct()[:limit]

    return [r.to_dict() for r in rooms]


def club_rules_and_info(query, limit=5):
    search_results = SearchIndex\
        .search(query)\
        .filter(
            Q(post__slug__in=CLUB_INFO_POST_SLUGS) |
            Q(post__label_code=CLUB_INFO_POST_LABEL) |
            Q(post__type=Post.TYPE_DOCS)
        )[:limit]
    return [shorten_content_text(r.post.to_dict(including_private=True)) for r in search_results]


def shorten_content_text(post_or_comment_dict):
    result = dict(post_or_comment_dict)
    if "content_text" in result:
        result["content_text"] = result["content_text"][:TRIM_LONG_CONTENT_TO_LEN]
    if "text" in result:
        result["text"] = result["text"][:TRIM_LONG_CONTENT_TO_LEN]
    return result


TOOLS_MAP = {
    "search_posts": search_posts,
    "search_comments": search_comments,
    "search_users": search_users,
    "search_chats": search_chats,
    "generic_search": generic_search,
    "club_rules_and_info": club_rules_and_info,
}

TOOLS_DESCRIPTION = [
    {
        "type": "function",
        "name": "search_posts",
        "description": "Поиск постов соответствующих данному запросу, с возможностью фильтрации по типу и сортировки",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Упрощенный поисковый запрос или ключевые слова для поиска постов"
                },
                "post_type": {
                    "type": ["string", "null"],
                    "enum": [t[0] for t in Post.TYPES],
                    "description": f"Опциональный фильтр по типа поста из списка: {Post.TYPES}. "
                                   f"Pass null if not needed.",
                },
                "order_by": {
                    "type": ["string", "null"],
                    "enum": list(ALLOWED_ORDERING),
                    "description": "Опциональная сортировка постов. Default is '-rank'.",
                },
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "search_comments",
        "description": "Поиск комментариев пользователей по поисковому запросу или ключевым словам",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Упрощенный поисковый запрос для поиска комментариев"
                },
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "search_users",
        "description": "Поиск людей в коммьюнити по имени, городам, месту работы, их биографии или увлечениям",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Упрощенный поисковый запрос или ключевые слова для поиска пользователей"
                },
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "search_chats",
        "description": "Поиск по тематическим чатам внутри коммьюнити по поисковому запросу или ключевым словам",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Упрощенный поисковый запрос или ключевые слова для поиска релевантных чатов"
                },
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "generic_search",
        "description": "Общий поиск любой информации (из постов, комментариев, пользователей) внутри коммьюнити "
                       "по поисковому запросу или ключевым словам",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Упрощенный поисковый запрос или ключевые слова для поиска релевантного контента"
                },
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "club_rules_and_info",
        "description": "Поиск ответов на вопросы о самом Клубе: правилах, инструкциях, модерации, ценностях, "
                       "советах новичкам, вопросам членства, оплате и рефандах",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Ключевые слова для поиска информации о Клубе"
                },
            },
            "required": ["query"],
            "additionalProperties": False
        }
    }
]

