import string
from datetime import datetime
from random import choice, randint
from typing import List

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management.base import BaseCommand

from auth.helpers import create_fake_user
from comments.models import Comment
from posts.models.post import Post

AVATARS_POST = "https://vas3k.club/post/11666/"
PICS_POST = "https://vas3k.club/guide/11689/"
WORDS_IN_PARAGRAPH = 100


class Command(BaseCommand):
    help = "Creates fake post with amount of comments"

    def add_arguments(self, parser):
        parser.add_argument('--words', type=int, default=600, help="Количество слов в посте")
        parser.add_argument('--pics', type=int, default=0, help="Количество картинок в посте")
        parser.add_argument('--comments', type=int, default=10, help="Количество комментариев первого уровня")
        parser.add_argument(
            '--deep-comments',
            type=int,
            default=0,
            help="Количество комментариев второго уровня у каждого комментария первого уровня"
        )

    def handle(self, *args, **options):
        if not (settings.DEBUG or settings.TESTS_RUN):
            print("Эта фича доступна только при DEBUG=true")
            exit(1)

        avatars = list(self._get_avatars())

        author = create_fake_user(avatar=choice(avatars))
        Post.upsert_user_intro(author, "Интро как интро, аппрув прошло :Р", is_visible=True)

        print("Создаем пост")
        post = Post(
            type=Post.TYPE_POST,
            author=author,
            title="Тестовый пост",
            text=self._create_text(words=options["words"], pics=options["pics"]),
            is_visible=True,
            published_at=datetime.utcnow()
        )
        post.save()

        if options.get("comments"):
            print("Создаем комменты")
            for _ in range(options["comments"]):
                comment_author = create_fake_user(avatar=choice(avatars))

                comment = Comment(
                    author=comment_author,
                    post=post,
                    text=self._create_text(words=randint(5, 50)),
                )
                comment.save()

                for __ in range(options["deep_comments"]):
                    comment_author = create_fake_user(avatar=choice(avatars))

                    deep_comment = Comment(
                        author=comment_author,
                        post=post,
                        reply_to=comment,
                        text=self._create_text(words=randint(5, 50)),
                    )
                    deep_comment.save()

            Comment.update_post_counters(post)

        print("Готово")

    def _get_avatars(self) -> List[str]:
        print("Скачиваем аватарки")

        res = requests.get(AVATARS_POST)
        if res.status_code != 200:
            print(f"Похоже публичный пост { AVATARS_POST } был скрыт. Спросите у Вастрика.")
            exit(1)

        tree = BeautifulSoup(res.text, features="lxml")
        avatars = set()
        for avatar_block in tree.find_all(attrs={"class": "avatar"}):
            img = avatar_block.find("img")
            if img:
                avatars.add(img.attrs["src"])

        print("Готово")
        return list(avatars)

    def _get_pics(self) -> List[str]:
        print("Скачиваем картинки")

        res = requests.get(PICS_POST)
        if res.status_code != 200:
            print(f"Похоже публичный пост { PICS_POST } был скрыт. Спросите у Вастрика.")
            exit(1)

        tree = BeautifulSoup(res.text, features="lxml")
        pics = set()
        for img_block in tree.find_all("figure"):
            img = img_block.find("img")
            if img:
                pics.add(img.attrs["src"])

        print("Готово")
        return list(pics)

    def _create_text(self, words: int, pics: int = 0) -> str:
        text = ""
        count = 0
        pic_links = []

        if pics:
            pic_links = self._get_pics()

        for _ in range(words):
            word = "".join(choice(string.ascii_lowercase) for _ in range(randint(3, 10)))
            text += word + " "
            count += 1

            if count == WORDS_IN_PARAGRAPH:
                text += "\n\n"
                count = 0

                if pics:
                    text += f"![]({ choice(pic_links) })\n\n"
                    pics -= 1

        for _ in range(pics):
            text += f"![]({choice(pic_links)})\n"

        return text
