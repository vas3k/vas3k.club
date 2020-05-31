FROM python:3.8-slim-buster

ENV DEBIAN_FRONTEND noninteractive

# required to build gdal (geo library)
ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal

RUN apt-get update \
    && apt-get dist-upgrade -y \
    && apt-get install --no-install-recommends -yq \
      gcc \
      g++ \
      libc-dev \
      libpq-dev \
      gdal-bin \
      libgdal-dev \
      make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install requirements into a separate layer
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
RUN python -c "import nltk; nltk.download('punkt')"

# copy the code
COPY . /app
COPY ./vas3k_club.env /app/club/.env
