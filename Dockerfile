FROM ubuntu:24.04
ENV MODE dev
ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_BREAK_SYSTEM_PACKAGES=1

RUN apt-get update \
    && apt-get install --no-install-recommends -yq \
      build-essential \
      python3 \
      python3-dev \
      python3-pip \
      libpq-dev \
      gdal-bin \
      libgdal-dev \
      make \
      npm \
      cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app
COPY etc/crontab /etc/crontab
RUN chmod 600 /etc/crontab

RUN cd frontend && npm ci && npm run build && cd ..

RUN pip3 install pipenv
RUN if [ "$MODE" = "production" ]; then \
        pipenv requirements --keep-outdated > requirements.txt; \
    elif [ "$MODE" = "dev" ]; then \
        pipenv requirements --dev > requirements.txt; \
    fi

RUN pip3 install --ignore-installed -r requirements.txt
