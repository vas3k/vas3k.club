# Гайд по техническому управлению клубом

Админка клуба — кастомный **godmode** на `/godmode/` (не Django Admin). Доступ есть у пользователей с ролями `curator` / `moderator` / `bank` / `god` (в зависимости от раздела).

## Как получить доступ в godmode (локально)

1. Поднять проект (`docker compose up`)
2. Открыть http://127.0.0.1:8000/godmode/dev_login/ — создастся пользователь `dev` с ролью `god` и вас залогинит
3. Открыть `/godmode/`

## Как стать богом на проде / форке

1. Зарегистрироваться в клубе как обычно (заполнить анкету)
2. В консоли сервера:

```sh
docker exec -it club_app python3 manage.py shell
```

```python
from users.models.user import User
user = User.objects.get(slug="<ваш slug>")
user.moderation_status = "approved"
user.roles = ["god"]
user.save()
```

3. Проверить, что открывается `/godmode/`

## Как создать комнату

1. Открыть `/godmode/rooms/`
2. Create → заполнить поля:
   - `slug` — кусок URL комнаты
   - `title` — название
   - `subtitle` — подзаголовок
   - `image` / `icon` — картинка или иконка
   - `description` — описание
   - `color` — цвет плашки (`#RGB`)
3. Save

## Как добавлять клубные теги

1. Править `common/data/tags.py`
2. Задеплоить
3. На сервере: `docker exec -it club_app python3 manage.py update_tags`

## Как добавлять коллекционные теги

Тег добавляется автором поста при создании/редактировании — блок «Прикрепить коллекционный тег».

## Как редактировать лейблы постов

1. Править `common/data/labels.py`
2. Задеплоить

## Как назначить посту лейбл

1. Зайти под куратором или выше
2. На странице поста открыть инструменты (справа)
3. «Выдать лейбл»

## Как редактировать ачивки

1. Править `common/data/achievements.py`
2. Задеплоить
3. На сервере: `docker exec -it club_app python3 manage.py update_achievements`

## Как выдать ачивку участнику

1. Зайти под модератором или выше
2. Профиль участника → «админка» → блок «Ачивки»
3. Выбрать ачивку и сохранить

Либо через `/godmode/users/<id>/action/achievement/` (и аналогичные actions в godmode).

## Как одобрять новых пользователей

1. Создать чат для модерации, добавить туда бота клуба
2. Прописать `TELEGRAM_ADMIN_CHAT_ID` в секреты / `.env`
3. Задеплоить — в чат будут падать новые анкеты

## Как выдать роль участнику

1. `/user/<username>/` → «Админка» → блок «Роли»
2. Роли:
   - **Куратор** — лейблы, поднять/скрыть с главной и т.п.
   - **Модератор** — всё выше + закрыть комменты, модерация участников
   - **Банк** — добавлять дни участникам
   - **Бог** — может всё

## Как сделать дамп базы

```sh
docker exec club_postgres pg_dump --clean --if-exists --no-owner --no-privileges \
  "host=localhost port=5432 dbname=vas3k_club user=postgres password=postgres" \
  | gzip > dump.sql.gz
```

На проде пользователь/пароль другие — смотрите свои env-переменные.

## Как залить дамп базы

```sh
docker cp dump.sql.gz club_postgres:/tmp/
docker exec -it club_postgres bash
cd /tmp && gunzip dump.sql.gz
psql -d vas3k_club -h localhost -U postgres -w < dump.sql
```

## У меня не получается, что делать?

Вопросы по этому гайду можно адресовать [автору](https://vas3k.club/user/glader/). Общие вопросы по коду — в [dev-чат](https://t.me/vas3k_club_dev) (но не про ваши форки).
