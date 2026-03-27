<div align="center">
  <br>
  <img src="gitstatic/logo-pmi.png" alt="PMI Moscow club">
  <h1>PMI Moscow club</h1>
</div>

## TESTS
[![Run tests](https://github.com/TopTuK/pmi.moscow.club/actions/workflows/tests.yml/badge.svg)](https://github.com/TopTuK/pmi.moscow.club/actions/workflows/tests.yml)
[![Check it could be build and run from scratch](https://github.com/TopTuK/pmi.moscow.club/actions/workflows/check_build_and_run.yml/badge.svg)](https://github.com/TopTuK/pmi.moscow.club/actions/workflows/check_build_and_run.yml)

## RU
Привет! Этот проект содержит исходники [PM Russia](https://pmi.moscow) клуба. Мы строим наше комьюнити экпертов в управлении проектами вокруг института [PMI](https://pmi.org). В 2022 году равление PMI приняло решение о приостановке детяльности локальных отделений PMI в России, Беларуси, ДНР и ЛНР, поэтому нами было принято решение о создании временно независимого сообщества экпертов, главнами ценностями которого являются люди, их знания, навыки и опыт.

Проект строится на кодовой базе [vas3k.club](https://vas3k.club), является форком [кодовой базы](https://github.com/vas3k/vas3k.club). Проект открыт к измениям, мы приветствуем новых участников и контрибьютеров.

Членство в клубе является приватным и строится членами института управления проектами PMI. Мы строим мирное и полезное сообщество. где каждый участник может найти для себя различную полезную информацию об управлении проектами, создании новых уникальных продуктов, услуг или конечных результатов.

## EN
TBD: перевести.

## 🛠 Технический стек
👨‍💻 **TL;DR: Django, Postgres, Redis, Vue.js, Webpack**
Оригинальная информация доступна тут: [vas3k.club](https://github.com/vas3k/vas3k.club)

## 🧑‍💻 Хочу покодить

### 🔮 Простой способ запуска платформы клуба

1. Установить [Docker](https://www.docker.com/get-started)
2. Клонировать репозитарий

  ```sh
  $ git clone https://github.com/TopTuK/pmi.moscow.club.git
  $ cd pmi.moscow.club
  ```

3. Создать и отредактировать .env файл

  ```sh
  $ cd club
  $ cp .env.example .env
  ```
  Ключевые параметры:
  ```
  POSTGRES_USER="postgres"
  POSTGRES_PASSWORD="postgres"

  MEDIA_UPLOAD_URL="pepic_url"
  MEDIA_UPLOAD_CODE="pepic_code"

  EMAIL_HOST="mail_host"
  EMAIL_HOST_USER="mail_sender_user"
  EMAIL_HOST_PASSWORD="mail_sender_user_password"
  ```

4. Запустить сервисы

  ```sh
  $ docker compose up
  ```

### 🔮 Простой способ запуска платформы клуба
Для локальной разработки, тестирования телеграм ботов, запуск платформы без Docker инструкция здесь: [docs/setup.md](docs/setup.md).

### Хочу сделать свой Клуб
Инструкция по созданию Клуба:
- https://teletype.in/@toptuk/pmiclub1
- https://teletype.in/@toptuk/pmiclub2
- https://teletype.in/@toptuk/pmiclub3
- https://teletype.in/@toptuk/pmiclub4
- https://teletype.in/@toptuk/pmiclub5
- https://teletype.in/@toptuk/pmiclub6

## 👩‍💼 Лицензия (License)

[MIT](LICENSE)

❤️ Meow! ❤️
Auto-reloading for backend and frontend is performed automatically on every code change. If everything is broken and not working (it happens), you can always rebuild the world from scratch using `docker compose up --build`.

## 🧑‍💻 Advanced setup for devs

For more information on how to test the telegram bot, run project without docker and other useful notes, read [docs/setup.md](docs/setup.md).

## ☄️ Testing

We use standard Django testing framework for backend and Jest for frontend. No magic, really.

See [docs/test.md](docs/test.md) for more insights.

## 🚢 Deployment

No k8s, no AWS, we ship dockers directly via ssh and it's beautiful!

The entire production configuration is described in the [docker-compose.production.yml](docker-compose.production.yml) file. 

Then, [Github Actions](.github/workflows/deploy.yml) have to take all the dirty work. They build, test and deploy changes to production on every merge to master (only official maintainers can do it).

Explore the whole [.github](.github) folder for more insights.

We're open for proposals on how to improve our deployments without overcomplicating it with modern devops bullshit.

## 🛤 Forking and tweaking

Forks are welcome. We're small and our engine is not universal like Wordpress, but with sufficient programming skills (and using grep), you can launch your own Club website in a couple of weeks. 

Three huge requests for everyone:

- Please give kudos the original authors. "Works on vas3k.club engine" in the footer of your site will be enough.
- Please share new features you implement with us, so other folks can also benefit from them, and your own codebase minimally diverges from the original one (so you can sync updates and security fixes) . Use our [feature-flags](club/features.py).
- Do not use our "issues" and chats as a support desk for your own fork.

> ♥️ [Feature-flags](club/features.py) are great. Use them to tweak your fork. Create new flags to upstream your new features or disable existing ones.

## 🙋‍♂️ How to report a bug or propose a feature?

- 🆕Open [a new issue](https://github.com/vas3k/vas3k.club/issues/new) using one of the existing templates. 
- 🔦 Please, **use the search function** to make sure you aren't creating a duplicate.
- 🖼 Provide ALL the details, screenshots, logs, etc. Bug reports without steps to reproduce will be closed.

## 😍 Contributions

Important information for everyone willing to contribute to this project.

- AI-generated PRs are NOT welcome.
- Low-effort PRs are NOT welcome.
- No cowboy PRs without prior discussion AND approval from maintainers.
- 1 PR = 1 feature. No PRs with bulk changes.
- Any PR longer than 10 lines of code must include a detailed text explanation of all changes.

**A good way to contribute bug fixes:** search the Issues to make sure the bug hasn't been reported yet. Open a new Issue with a detailed description and steps to reproduce. Open a PR with the fix (if you can), then the contributors will either merge your PR or you'll carry on the discussion in the comments.

**For new features:** open a new Issue describing the new feature you're interested in. Wait for the contributors to get back to you and give you the green light for implementation. If the contributors don't reply, it means the feature isn't of interest at the moment. ONLY after that should you open a PR for that feature.

The main point of interaction is the [Issues page](https://github.com/vas3k/vas3k.club/issues) and our [Dev-chat in telegram](https://t.me/vas3k_club_dev). DO NOT DISCUSS FORKS THERE.

If you want to contribute but don't know where to start — come to the chat and just ask! 

> The official development language at the moment is Russian, because 100% of our users speak it. We don't want to introduce unnecessary barriers for them. But we are used to writing commits and comments in English and we won't mind communicating with you in it.

## 🔐 Security and vulnerabilities

If you think you've found a critical vulnerability that should not be exposed to the public yet, you can always email me directly on Telegram [@vas3k](https://t.me/vas3k) or by email: [me@vas3k.ru](mailto:me@vas3k.ru).

Please do not test vulnerabilities in public. If you start spamming the website with "test-test-test" posts or comments, our moderators will ban you even if you had good intentions.

## 👩‍💼 License 

[MIT](LICENSE)

You can use the code for your own private or commercial purposes with an author attribution (by including the original license file and mentioning vas3k.club somewhere on your website 🎩).

Feel free to contact us via email [club@vas3k.club](mailto:club@vas3k.club).

❤️
