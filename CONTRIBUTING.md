# How to contribute

Bug reports and pull requests from users are what keep this project working.

## 😍 Contributions

Contributions are welcome.  

The main point of interaction is the [Issues page](https://github.com/vas3k/vas3k.club/issues).

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

- **For big changes** open an issues first or (if it's already opened) leave a comment with brief explanation what and why you're going to change. Many tickets hang open not because they cannot be done, but because they cause many logical contradictions that you may not know. It's better to clarify them in comments before sending a PR.

  #### 🚦Pay attention to issue labels classification:

  ##### 🟩 Ready to implement:

- **good first issue** — good tickets **for first-timers**. Usually these are simple and not critical things that allow you to quickly feel the code and start contributing to it.
- **bug** — the **first priority**, obviously.

- **improvement** — accepted improvements for an existing module. Like adding a sort parameter to the feed. If improvement requires UI, **be sure to provide a sketch before you start.**

  ##### 🟨 Discussion is needed:

- **new feature** —  completely new features. Usually they're too hard for newbies, leave them **for experienced contributors.** 

- **idea** — **discussion is needed**. Those tickets look adequate, but waiting for real proposals how they will be done. Don't implement them right away.

  ##### 🟥 Questionable:

- [¯\\_(ツ)_/¯](https://github.com/vas3k/vas3k.club/labels/ ̄\_(ツ)_%2F ̄) - special label for **questionable issues**. (should be closed in 60 days of inactivity)

- **<no label>** — ticket is new or controversial. Feel free to discuss it but **wait for our maintainers' decision** before starting to implement it.

## Basics

1. Create an issue and describe your idea
2. [Fork it](https://github.com/vas3k/vas3k.club/fork)
3. Create your feature branch (`git checkout -b my-new-feature`)
4. Commit your changes (`git commit -am 'Add some feature'`)
5. Publish the branch (`git push origin my-new-feature`)
6. Create a new Pull Request on Github (if you are new with Github: [here is tutorial](https://guides.github.com/activities/hello-world/)

---

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

At the very beginning, you probably need a dev account to log in. Open [http://127.0.0.1:8000/godmode/dev_login/](http://127.0.0.1:8000/godmode/dev_login/) in your browser and it will create one for you and log you in.

- To create new test user: open [http://127.0.0.1:8000/godmode/random_login/](http://127.0.0.1:8000/godmode/random_login/)

Auto-reloading for backend and frontend is performed automatically on every code change. If everything is broken and not working (it happens), you can always rebuild the world from scratch using `docker-compose up --build`.

## 🧑‍💻 Advanced setup for developers

See [docs/setup.md](docs/setup.md)

## ☄️ Testing

We use standard Django testing framework.

See [docs/test.md](docs/test.md)

## 🚢 Deployment

CI/CD has setuped via github-actions. Go further to the [.github](.github/) folder to see details.

:point_up: We still need someone who will improve and optimize ci workflows
