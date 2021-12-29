FROM python:3-alpine

WORKDIR /tg/

RUN pip install python-telegram-bot

COPY send_message.py /tg/send_message.py

ENTRYPOINT ["python", "/tg/send_message.py"]
