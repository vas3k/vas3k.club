<div align="center">
  <br>
  <img src="frontend/static/images/logo/logo-256.png" alt="">
  <h1>vas3k.club</h1>
</div>

Welcome to the [vas3k.club](https://vas3k.club) codebase. Here we are building our small lifestyle IT community. If you want to help us with that, welcome.

[vas3k.club](https://vas3k.club) is a platform with private and paid memberships that has emerged around the [vas3k.ru](https://vas3k.ru) blog and satellite chat rooms. It's not a typical IT community with tutorials and framework reviews, but rather more of a lifestyle one. We are trying to build a peaceful and useful ecosystem, which the Internet has lost a long ago. Therefore, we carefully select and filter new members and do not seek wild growth.

Our values: honesty, fair share, respect for other members, rationality, friendliness and usefulness. We have a zero-tolerance policy on anonymity, insults and toxicity. But we always try to stay in touch with reality, so we're also not tolerant of witch hunting and call-out culture.

We're a bullshitless community!

## 🛠 Tech stack

👨‍💻 **TL;DR: Django, Postgres, Redis, Vue.js, Webpack**

We try to keep our stack as simple and stupid as possible. Because we're not very smart either.

> This section is in progress...

## 🔮 Installing and running locally

1. Install [Docker](https://www.docker.com/get-started)

2. Clone the repo

    ```sh
    $ git clone https://github.com/vas3k/vas3k.club.git
    $ cd vas3k.club
    ```

3. Run

    ```sh
    $ docker-compose up
    ```

It will start the development server with all the necessary services. Wait till it starts and go to [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Voila.

At the very beginning, you probably need a dev account to log in. Open [/godmode/dev_login/](http://127.0.0.1:8000/godmode/dev_login/) in your browser and it will make one for you (and log you in automatically).  To create new test user hit the [/godmode/random_login/](http://127.0.0.1:8000/godmode/random_login/) endpoint.

Auto-reloading for backend and frontend is performed automatically on every code change. If everything is broken and not working (it happens), you can always rebuild the world from scratch using `docker-compose up --build`.

## 🧑‍💻 Advanced setup for developers

For more information on how to test the telegram bot, run project without docker and other useful notes, read [docs/setup.md](docs/setup.md).

## ☄️ Testing

We use standard Django testing framework. No magic, really. You can run them from PyCharm or using Django CLI. 

See [docs/test.md](docs/test.md) for more insights.

> We don't have UI tests, sorry. Maybe in the future

## 🚢 Deployment

Automatic CI/CD pipelines are building and testing the app on each PR. They also deploy changes to production on merge to master (only a maintainer can do it).

These pipelines are made as github-actions. Explore the [.github](.github) folder for more.

:point_up: We still need someone to improve and optimize our CI workflows. They work but they're really poor :D


## 😍 Contributions

Contributions are welcome.  

The main point of interaction is the [Issues page](https://github.com/vas3k/vas3k.club/issues).

Here's our contribution guidelines — [CONTRIBUTING.md](CONTRIBUTING.md).

We also run the public [Github Project Board](https://github.com/vas3k/vas3k.club/projects/3) to track progress and develop roadmaps.

> The official development language at the moment is Russian, because 100% of our users speak it. We don't want to introduce unnecessary barriers for them. But we are used to writing commits and comments in English and we won't mind communicating with you in it.

### 🙋‍♂️ How to report a bug or propose a feature?

- 🆕Open [a new issue](https://github.com/vas3k/vas3k.club/issues/new). 
  - 🔦 Please, **use a search**, to check, if there is already exied issue!
- Explain your idea or proposal in all the details: 
  - If it's a **new feature**:
    - 🖼 If it's **UI/UX** related: attach a screenshot or wireframe.
    - Please mark this issues with prefix **"Фича:"**
  - 🐞 If it's a **bug**:
    - make sure you clearly describe "observed" and "expected" behaviour. It will dramatically save time for our contributors and maintainers. 
    - **For minor fixes** please just open a PR.
    - *Please mark this issues with prefix **"Баг:"***

### 😎 I want to write some code!

- Open our [Issues page](https://github.com/vas3k/vas3k.club/issues) to see the most important tickets at top. 
- Pick one issue you like and **leave a comment** inside that you're getting it.

**For big changes** open an issues first or (if it's already opened) leave a comment with brief explanation what and why you're going to change. Many tickets hang open not because they cannot be done, but because they cause many logical contradictions that you may not know. It's better to clarify them in comments before sending a PR.

### 🚦Pay attention to issue labels classification

##### 🟩 Ready to implement

- **good first issue** — good tickets **for first-timers**. Usually these are simple and not critical things that allow you to quickly feel the code and start contributing to it.
- **bug** — the **first priority**, obviously.

- **improvement** — accepted improvements for an existing module. Like adding a sort parameter to the feed. If improvement requires UI, **be sure to provide a sketch before you start.**

##### 🟨 Discussion is needed

- **new feature** —  completely new features. Usually they're too hard for newbies, leave them **for experienced contributors.** 

- **idea** — **discussion is needed**. Those tickets look adequate, but waiting for real proposals how they will be done. Don't implement them right away.

##### 🟥 Questionable

- [¯\\_(ツ)\_/¯](https://github.com/vas3k/vas3k.club/labels/%C2%AF%5C_%28%E3%83%84%29_%2F%C2%AF) - special label for **questionable issues**. (should be closed in 60 days of inactivity)

- **[no label]** — ticket is new or controversial. Feel free to discuss it but **wait for our maintainers' decision** before starting to implement it.

## 👍 Our top contributors

Take some time to press F and give some respects to our [best contributors](https://github.com/vas3k/vas3k.club/graphs/contributors), who spent their own time to make the club better.

- [@vas3k](https://github.com/vas3k)
- [@nlopin](https://github.com/nlopin)
- [@fr33mang](https://github.com/fr33mang)
- [@Vostenzuk](https://github.com/Vostenzuk)
- [@nikolay-govorov](https://github.com/nikolay-govorov)
- [@FMajesty](https://github.com/FMajesty)


## 👩‍💼 License 

[MIT](LICENSE)

In other words, you can use the code for private and commercial purposes with an author attribution (by including the original license file or mentioning the Club 🎩).

Feel free to contact us via email [club@vas3k.club](mailto:club@vas3k.club).

❤️
