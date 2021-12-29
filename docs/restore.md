# Восстановление

Этот документ описывает процедуру восстановления 4aff после падения сервиса.

## Prerequisites
- виртуальный сервер с root доступом
- дамп базы
- архив картинок

## Восстановление для проверки работоспособности
- `apt update && apt install -y nginx mc ca-certificates curl gnupg lsb-release`
- `curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg`
- `mkdir -p /etc/apt/sources.list.d && echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null`
- `apt-get update && apt-get install docker-ce docker-ce-cli containerd.io`
- `curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose`
- `chmod +x /usr/local/bin/docker-compose && ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose`
- `mkdir -p /var/www/4aff.club`
- `echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDCtyphHRSZ0rmwy3UpmCrOMHt6QioLfeh3/4+fkK6k3w2Dtf+sMC6Aa7JHSRvtkei+LVNFchoQ+puqN+vPSLul/ZyJYLYvSVqKt4qMKuhWbXWJzhKxq7dxKMxoEOinrm2zMAgVLn2Ix7fjIONiiFaRUcSwOP/5D3078cexsEAqJHqwOihtYOeb+KUJk/p74ZOye5KXK3Nq+fprGIAx2uGuPPvhuKLZPiego0+ssAX2KHWIk34Gth3o/496TuPOx1ZaJjkghlBXB+aHRiW2DNLro9JoVfCAaHrsnRtzKR5PpIS8B+po7yhQbh7xCu5S8JOPCpsfwPBycBTKBqlkeuWb github" >> /root/.ssh/authorized_keys`

- зайти в https://github.com/glader/4aff.club/settings/secrets/actions, изменить `PRODUCTION_SSH_HOST` на ip-адрес нового сервера
- зайти в https://github.com/glader/4aff.club/actions, выбрать самый свежий запуск с описанием "Deploy master to production", зайти внутрь, нажать "re-run all jobs"

- `cd /etc/nginx/sites-enabled`
- `wget https://raw.githubusercontent.com/glader/4aff.club/4aff/etc/nginx/4aff.club.conf`
- `wget https://raw.githubusercontent.com/glader/4aff.club/4aff/etc/nginx/i.4aff.club.conf`
- `wget https://raw.githubusercontent.com/glader/4aff.club/4aff/etc/nginx/og.4aff.club.conf`
- `/etc/init.d/nginx restart`

- посмотреть на сервере бекапа самый свежий файл в `backup/4aff/current`
- `scp  -o StrictHostKeyChecking=no username@username.backup.ihc.ru:/backup/p605083/backup/4aff/current/4aff_20211228_1200.pgsql.gz /tmp/`
- `scp  -o StrictHostKeyChecking=no username@username.backup.ihc.ru:/backup/p605083/backup/4aff/uploads.tar /tmp/`
- `docker cp 4aff_20211228_1200.pgsql.gz club_postgres:/tmp/dump.sql.gz`
- `docker exec club_postgres gunzip /tmp/dump.sql.gz`
- `docker exec club_postgres psql -d vas3k_club -U vas3k --file=/tmp/dump.sql`

## Дополнительные действия
- https
- og
- поставить пепик
- поправить конфиг пепика
- развернуть картинки в пепик
