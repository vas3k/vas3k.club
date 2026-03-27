import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta

from django.db import connections
from django.conf import settings
from django.core.management import BaseCommand

from posts.models.post import Post
from users.models.user import User
from comments.models import Comment
from common.markdown.markdown import markdown_text
from utils.strings import random_string

headers = {'User-Agent': 'posts-to-dev'}

# отключаем foreign keys, т.к. некоторые ответы на комменты имеют более ранний created_at, что приводит
# к ошибке. по сути коммент ссылается на тот, которого ещё нет в базе.
connection = connections['default']
with connection.cursor() as cursor:
    cursor.execute('SET session_replication_role TO \'replica\';')


class Command(BaseCommand):
    help = "Импорт постов с оригинального PMI Moscow на dev/local сборки"

    def add_arguments(self, parser):
        parser.add_argument(
            "--pages",
            type=int,
            default=1,
            help="Количество страниц, забираемых из фида",
        )

        parser.add_argument(
            "--skip",
            type=int,
            default=0,
            help="Количество страниц, которые надо пропустить",
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="Заменять посты, если они уже существуют",
        )

        parser.add_argument(
            "--with-comments",
            action="store_true",
            help="В том числе парсить комменты (требуется service_token)",
        )

        parser.add_argument(
            "--with-private",
            action="store_true",
            help="В том числе парсить приватные посты (требуется service_token)",
        )

        parser.add_argument(
            "--service-token",
            help="service_token приложения, требуется для приватных постов и парсинга комментариев. Получить можно тут: https://pmi.moscow/apps/create/",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            return self.stdout.write("☢️  Только для запуска в DEBUG режиме")

        if options["service_token"]:
            headers.update({'X-Service-Token': options["service_token"]})
            req = urllib.request.Request("https://pmi.moscow/user/me.json", headers=headers)
            try:
                urllib.request.urlopen(req)
            except urllib.error.HTTPError:
                return self.stdout.write(" ⛔ Неверный service_token")

        if (options["with_comments"] or options["with_private"]) and not options["service_token"]:
            return self.stdout.write(
                " ⛔ Флаги --with-comments и --with-private доступны только если указать --service-token")

        result = {
            'post_exists': 0,
            'post_created': 0,
            'post_updated': 0,
            'user_created': 0,
            'comment_created': 0,
        }

        for x in range(options['skip'], options['pages'] + options['skip']):
            url = f"https://pmi.moscow/feed.json?page={x + 1}"
            self.stdout.write(f"📁 {url}")
            req = urllib.request.Request(url, headers=headers)
            response = urllib.request.urlopen(req)
            data = json.load(response)
            for item in data['items']:
                # приватные нафиг
                if not item['_club']['is_public'] and not options['with_private']:
                    continue

                author, created = create_user(item['authors'][0])
                if created:
                    result['user_created'] += 1
                    self.stdout.write(f" 👤 \"{author.full_name}\" пользователь создан")

                *_, slug, _ = item['url'].split('/')

                defaults = dict(
                    id=item['id'],
                    title=item['title'],
                    type=item['_club']['type'],
                    slug=slug,
                    text=item['content_text'],
                    html=markdown_text(item['content_text']),
                    created_at=item['date_published'],
                    last_activity_at=item['date_modified'],
                    comment_count=item['_club']['comment_count'],
                    view_count=item['_club']['view_count'],
                    upvotes=item['_club']['upvotes'],
                    is_commentable=True,
                    moderation_status=Post.MODERATION_APPROVED,
                    is_public=item['_club']['is_public'],
                    author_id=author.id,
                    published_at=item['date_published'],
                    coauthors=[]
                )

                if item['_club']['type'] == "project":
                    defaults['image'] = author.avatar,  # хак для постов типа "проект", чтобы не лазить по вастрику лишний раз

                try:
                    post = Post.objects.get(id=item['id'])
                    if not options['force']:
                        result['post_exists'] += 1
                        self.stdout.write(f" 📌 \"{item['title']}\" уже существует")
                        continue
                    else:
                        post.__dict__.update(**defaults)
                        post.save()
                        result['post_updated'] += 1
                        self.stdout.write(f" 📝 \"{item['title']}\" запись отредактирована")

                except Post.DoesNotExist:
                    post = Post.objects.create(**defaults)
                    post.last_activity_at=item['date_modified']
                    post.save()
                    result['post_created'] += 1
                    self.stdout.write(f" 📄 \"{item['title']}\" запись создана")

                if options['with_comments']:
                    comments = parse_comments(item['id'], item['url'])
                    result['comment_created'] += comments
                    self.stdout.write(f"  💬 к посту \"{item['title']}\" спаршено {comments} комментов")

        self.stdout.write("")
        self.stdout.write("Готово 🌮")
        self.stdout.write(f"📄 Новых постов: {result['post_created']}")
        self.stdout.write(f"📌 Уже существовало: {result['post_exists']}")
        self.stdout.write(f"📝 Отредактировано: {result['post_updated']}")
        self.stdout.write(f"👤 Новых пользователей: {result['user_created']}")
        self.stdout.write(f"💬 Новых комментов: {result['comment_created']}")


def create_user(author):

    if 'name' in author:
        name = author['name']
    else:
        name = author['full_name']

    defaults = dict(
        avatar=author['avatar'],
        email=random_string(30),
        full_name=name,
        company="FAANG",
        position="Team Lead конечно",
        balance=10000,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        membership_started_at=datetime.utcnow(),
        membership_expires_at=datetime.utcnow() + timedelta(days=365 * 100),
        is_email_verified=True,
        moderation_status=User.MODERATION_STATUS_APPROVED,
        roles=[],
    )
    if 'id' not in author:
        *_, slug, _ = author['url'].split('/')
        defaults.update(slug=slug)

        if 'X-Service-Token' in headers.keys():
            req = urllib.request.Request(f"https://pmi.moscow/user/{slug}.json", headers=headers)
            response = urllib.request.urlopen(req)
            data = json.load(response)
            defaults.update(**data['user'])
    else:
        defaults.update(**author)

    if 'is_active_member' in defaults.keys():
        defaults.pop('is_active_member')

    if 'payment_status' in defaults.keys():
        defaults.pop('payment_status')

    return User.objects.get_or_create(slug=defaults['slug'], defaults=defaults)


def parse_comments(post_id, url):
    req = urllib.request.Request(f"{url}comments.json", headers=headers)
    response = urllib.request.urlopen(req)
    data = json.load(response)
    comments = []
    for comment in data['comments']:
        if not Comment.objects.filter(id=comment['id']).exists():
            create_user(comment['author'])

            comments.append(Comment(
                id=comment['id'],
                text=comment['text'],
                author_id=comment['author']['id'],
                reply_to_id=comment['reply_to_id'],
                created_at=comment['created_at'],
                upvotes=comment['upvotes'],
                post_id=post_id,
            ))

    Comment.objects.bulk_create(comments, 100)
    return len(comments)
