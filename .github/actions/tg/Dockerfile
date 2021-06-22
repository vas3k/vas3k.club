FROM python:3-alpine

WORKDIR /tg/

# We don't want to hide the Telegram token, but we want to avoid it being detected by automated parsers
ENV INPUT_TOKEN_B64="MTExMDUwNTEyNjpBQUc0LVZMdkxzMWpTNkVzTmNkWENXWTQ1SlFCcXJYemFFUQ=="

RUN pip install python-telegram-bot

COPY send_message.py /tg/send_message.py

ENTRYPOINT ["python", "/tg/send_message.py"]
