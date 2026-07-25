# Чеклист по запуску форка vas3k.club

Примерный список действий, чтобы поднять сайт на движке Вастрика.

## Репозиторий

- [ ] Клонировать репу движка
- [ ] Создать ветку для деплоя
- [ ] Поправить GitHub Actions под свою ветку/хост
- [ ] Classic GitHub token с `write:packages`, `delete:packages` → секрет `TOKEN`

## Хостинг

- [ ] Сервер (~30 ГБ диск, ~4 ГБ RAM), root-доступ
- [ ] `apt install -y make mc nginx git certbot python3-certbot-nginx`
- [ ] SSH-ключ для деплоя → deploy key / `authorized_keys`
- [ ] Docker
- [ ] Каталог проекта (например `/var/projects/club`)

## DNS, Sentry, почта

- [ ] DNS домена на сервер
- [ ] Sentry DSN → секреты
- [ ] Почта (SES или аналог): SPF/DKIM, секреты SMTP, проверка отправки

## Картинки и OG

- [ ] [pepic](https://github.com/vas3k/pepic) для аплоада картинок + nginx + HTTPS
- [ ] [ogimgd](https://github.com/nDmitry/ogimgd) для OG-картинок + nginx + HTTPS
- [ ] Секреты `MEDIA_UPLOAD_URL` / `MEDIA_UPLOAD_CODE` в клубе

## Клуб и бот

- [ ] Nginx + certbot для клуба
- [ ] При необходимости отключить оплату на старте (feature-flags / настройки)
- [ ] Telegram-бот → `TELEGRAM_TOKEN` и связанные ID в секретах
- [ ] Чаты/каналы: модерация, общий чат, канал новостей, online-канал → соответствующие `TELEGRAM_*` секреты

## Первый запуск

- [ ] Задеплоить, залогиниться
- [ ] Выдать себе `roles=["god"]` через shell — см. [tech_guide.md](tech_guide.md#как-стать-богом-на-проде--форке)
- [ ] Открыть `/godmode/`
- [ ] Прогнать `update_tags` после правок тегов — см. [tech_guide.md](tech_guide.md#как-добавлять-клубные-теги)
- [ ] Создать комнаты в `/godmode/rooms/`

## Оформление

- [ ] Лендинг, about, contact, network
- [ ] Логотип / favicon
- [ ] Тексты: `frontend/html/docs`
- [ ] Письмо после оплаты

## Эксплуатация

- [ ] Бэкап БД и картинок
- [ ] Платёжный шлюз (Stripe / YooKassa / Patreon — что нужно)

## Что подготовить заранее

- Хостинг + место под бэкапы
- Тексты страниц, теги профиля, комнаты, логотип
- Бот и чаты/каналы (модерация, общий, новости, online)

## У меня не получается

Вопросы по чеклисту — [автору гайда](https://vas3k.club/user/glader/). Не используйте issues/dev-чат upstream как саппорт форка.
