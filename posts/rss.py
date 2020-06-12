from django.contrib.syndication.views import Feed

from posts.models import Post
from users.models.user import User


NO_ACCESS_DESCRIPTION = "Автор этого поста предпочёл скрыть его текст от Большого Интернета.<br><br>" \
                        "В <a href=\"https://vas3k.club/user/me/edit/notifications/\">настройках уведомлений</a> " \
                        "вы можете получить специальный URL вашей приватной ленты RSS, где будут отображаться " \
                        "в том числе и закрытые посты. Ссылка привязана к вашему аккаунту и " \
                        "работает пор пока вы член Клуба."


class NewPostsRss(Feed):
    title = "Вастрик.Клуб: Новые посты"
    link = "/feed.rss"
    description = ""
    limit = 20

    def items(self, feed):
        is_authorized = False
        if feed["hash"]:
            user = User.registered_members().filter(secret_hash=feed["hash"]).first()
            if user and user.is_paid_member:
                is_authorized = True

        posts = Post.visible_objects().order_by("-published_at", "-created_at")[:self.limit]
        return [{
            "title": rss_post_title(post, is_authorized),
            "description": rss_post_description(post, is_authorized),
            "link": post.get_absolute_url(),
        } for post in posts]

    def item_title(self, item):
        return item["title"]

    def item_description(self, item):
        return item["description"]

    def item_link(self, item):
        return item["link"]

    def get_object(self, request, *args, **kwargs):
        return {
            "hash": request.GET.get("hash")
        }


def rss_post_title(post, is_authorized):
    title = post.title
    if post.prefix:
        title = f"{post.prefix} " + title
    if not post.is_public and not is_authorized:
        title += " 🔒"
    return title


def rss_post_description(post, is_authorized):
    if post.is_public or is_authorized:
        return post.description
    return NO_ACCESS_DESCRIPTION
