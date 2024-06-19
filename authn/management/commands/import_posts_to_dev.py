import json
import urllib.request
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management import BaseCommand

from posts.models.post import Post
from users.models.user import User
from common.markdown.markdown import markdown_text
from utils.strings import random_string


class Command(BaseCommand):
    help = "Импорт постов с оригинального vas3k.club на dev/local сборки"

    def add_arguments(self, parser):
        parser.add_argument(
            "--pages",
            type=int,
            default=1,
            help="Количество страниц, забираемых и фида",
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

    def handle(self, *args, **options):
        if not settings.DEBUG:
            return self.stdout.write("☢️  Только для запуска в DEBUG режиме")

        result = {
            'post_exists': 0,
            'post_created': 0,
            'user_created': 0
        }

        for x in range(options['skip'], options['pages'] + options['skip']):
            url = "https://vas3k.club/feed.json?page={}".format(x + 1)
            self.stdout.write("📁 {}".format(url))
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            response = urllib.request.urlopen(req)
            data = json.load(response)
            for item in data['items']:
                # приватные нафиг
                if not (item['_club']['is_public']):
                    continue

                [created, author] = create_user(item['authors'][0])
                if created:
                    result['user_created'] += 1
                    self.stdout.write(" 👤 \"{}\" пользователь создан".format(author.full_name))

                post_data = dict(
                    id=item['id'],
                    title=item['title'],
                    type=item['_club']['type'],
                    slug=random_string(10),
                    text=item['content_text'],
                    html=markdown_text(item['content_text']),
                    image=author.avatar,  # хак для постов типа "проект", чтобы не лазить по вастрику лишний раз
                    created_at=item['date_published'],
                    last_activity_at=item['date_modified'],
                    comment_count=item['_club']['comment_count'],
                    view_count=item['_club']['view_count'],
                    upvotes=item['_club']['upvotes'],
                    is_visible=True,
                    is_visible_in_feeds=True,
                    is_commentable=True,
                    is_approved_by_moderator=True,
                    is_public=True,
                    author_id=author.id,
                    is_shadow_banned=False,
                    published_at=item['date_published'],
                    coauthors=[]
                )

                if Post.objects.filter(pk=item['id']).exists():
                    if options['force']:
                        Post.objects.filter(pk=item['id']).update(**post_data)
                    else:
                        result['post_exists'] += 1
                        self.stdout.write(" 📌 \"{}\" уже существует".format(item['title']))
                        continue
                else:
                    post = Post.objects.create(**post_data)
                    post.created_at = item['date_published']
                    post.last_activity_at = item['date_modified']
                    post.save()

                result['post_created'] += 1
                self.stdout.write(" 📄 \"{}\" запись создана".format(item['title']))

        self.stdout.write("")
        self.stdout.write("Итого:")
        self.stdout.write("📄 Новых постов: {}".format(result['post_created']))
        self.stdout.write("📌 Уже существовало: {}".format(result['post_exists']))
        self.stdout.write("👤 Новых пользователей: {}".format(result['user_created']))


def create_user(author):
    split = author['url'].split('/')
    slug = split[-2]

    if User.objects.filter(slug=slug).count() > 0:
        return [False, User.objects.get(slug=slug)]

    user = User.objects.create(
        slug=slug,
        avatar=author['avatar'],
        email=random_string(30),
        full_name=author['name'],
        company="FAANG",
        position="Team Lead конечно",
        balance=10000,
        membership_started_at=datetime.utcnow(),
        membership_expires_at=datetime.utcnow() + timedelta(days=365 * 100),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_email_verified=True,
        moderation_status=User.MODERATION_STATUS_APPROVED,
        roles=[],
    )
    user.save()

    return [True, user]
