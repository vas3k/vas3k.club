# Advanced Setup

## Telegram bot

To run telegram bot you have to:
  1. Copy env.exmaple file: `cp ./club/.env.example ./club/.env`
  2. Fill all the requirement fields in `./club/env`, such as `TELEGRAM_TOKEN` etc.
      - `TELEGRAM_TOKEN` you can get from [@BotFather](https://t.me/BotFather)
      - To get `TELEGRAM_CLUB_CHANNEL_URL`, `TELEGRAM_ADMIN_CHAT_ID` etc Just Simply Forward a message from your group/channel to [@JsonDumpBot](https://t.me/JsonDumpBot) or [@getidsbot](https://t.me/getidsbot)
  3. Rebuild application: `docker-compose up --build`

## Docker-compose

Check out our [docker-compose.yml](https://github.com/vas3k/vas3k.club/blob/master/docker-compose.yml) to understand the infrastructure.

## Local development

Once you decided to code something in the project you'll need to setup your environment. Here's how you can make it.

### Setup venv

Through `pipenv` // todo: (у меня с ним было 2 проблемы)
 - сходу не получилось выпилить установку gdal либы (удаление из pipfile и pipfile.locka не помогло), чтобы оно не фейлило установку остальных пакетов
 - не получилось указать папку созданного из консоли pipenv'а в pycharm'е

To mitigate gdal build failure (tested on ArchLinux):
1. Install gdal on your computer. Version must be same as one in `Pipfile.lock`.
   Probably you should compile it from sources.
2. Run `export CPLUS_INCLUDE_PATH=/usr/include/gdal C_INCLUDE_PATH=/usr/include/gdal`
   (I am not sure if this is neccessary)
3. Then run regular `pipenv install --dev`, it should work fine

Through old fashion `virtualenv`:
 - setup your Python Interpreter at PyCharm with `virtualenv`
 - install deps from [requirements.txt](requirements.txt) and [dev_requirements.txt](dev_requirements.txt)
  ```sh
  (venv) $ pip install --upgrade -r requirements.txt  
  (venv) $ pip install --upgrade -r dev_requirements.txt 
  ```

If you don't need to work with Geo Data and installation of `gdal` package is failed so skip it with next workaround:
```sh
# run each line of reqs independently
(venv) $ cat requirements.txt | xargs -n 1 pip install
```

### Setup postgres

#### locally
  Easies way is to run postgres is to run in docker, just run it with follow command:
  ```sh
  $ docker-compose -f docker-compose.yml up -d postgres
  ```
  When you need to connect to postgres use next params:
  ```dotenv
  POSTGRES_DB=vas3k_club
  POSTGRES_USER=postgres
  POSTGRES_PASSWORD=postgres
  POSTGRES_HOST=localhost
  ```

  <details><summary>In case you really want setup local postgres then go under cut...</summary>

    Brief instruction:
  
    1. Install postgresql (for macos https://postgresapp.com/ is easies start)
    2. After you install and run postgress create a project database:
          ```sh
          # create db
          $ psql postgres
          postgres=# createdb vas3k_club

          # create user (user: vas3k, password: vas3k)
          postgres=# createuser --interactive --pwpromp

          # grant priviliges
          postgres=# GRANT ALL PRIVILEGES ON DATABASE vas3k_club TO vas3k;
          postgres=# \connect vas3k_club
          postgres=# GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO vas3k;
          postgres=# GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public to vas3k;
          postgres=# GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public to vas3k;
          postgres=# \q

          # check connection
          $ psql -d vas3k_club -U vas3k
          ```

  </details>
  
#### Setup frontend
```sh
$ cd frontend
$ npm run watch # will implicitly run `npm ci`
```

#### Run dev server
After you have setup postgres, venv and build frontend (look this steps above) complete preparations with follow commands:
```sh
# run redis
$ docker-compose -f docker-compose.yml up redis

# run queue
(venv) $ ./manage.py qcluster

# run db migration
(venv) $ ./manage.py migrate

# run dev server
(venv) $ ./manage.py runserver 0.0.0.0:8000
```
