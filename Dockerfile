# stage for python dependency compilation
FROM ubuntu:20.04 as python-compile

WORKDIR /app

ENV MODE=dev
ENV DEBIAN_FRONTEND=noninteractive
ENV VIRTUAL_ENV=/opt/venv

RUN apt-get update \
    && apt-get install --no-install-recommends -yq \
      build-essential \
      python3 \
      python3-dev \
      python3-pip \
      python3-venv \
      libpq-dev \
      gdal-bin \
      libgdal-dev \
      make \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY Pipfile Pipfile.lock /app/

RUN pip install pipenv==2021.5.29
RUN sh -c 'if [ "$MODE" = 'production' ]; then pipenv lock --keep-outdated --requirements > requirements.txt; fi'
RUN sh -c 'if [ "$MODE" = 'dev' ]; then pipenv lock --dev --requirements > requirements.txt; fi'
RUN pip install -r requirements.txt

# final stage
FROM ubuntu:20.04
ENV MODE dev
ENV DEBIAN_FRONTEND=noninteractive
ENV VIRTUAL_ENV=/opt/venv

RUN apt-get update \
    && apt-get install --no-install-recommends -yq \
      python3 \
      make \
      npm \
      cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app
COPY etc/crontab /etc/crontab
RUN chmod 600 /etc/crontab

RUN cd frontend && npm install && npm run build && cd ..

COPY --from=python-compile $VIRTUAL_ENV $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
