FROM ubuntu:20.04
ENV MODE dev
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install --no-install-recommends -yq \
      python3 \
      python3-pip \
      libpq-dev \
      gdal-bin \
      libgdal-dev \
      make \
      npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN cd frontend && npm install && npm run build && cd ..

RUN pip3 install pipenv
RUN sh -c 'if [ "$MODE" = 'production' ]; then pipenv lock --keep-outdated --requirements > requirements.txt; fi'
RUN sh -c 'if [ "$MODE" = 'dev' ]; then pipenv lock --dev --requirements > requirements.txt; fi'
RUN pip3 install -r requirements.txt
RUN python3 -c "import nltk; nltk.download('punkt')"
