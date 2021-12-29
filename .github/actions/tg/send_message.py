import telegram
import os
import sys

token = sys.argv[1]
chat_id = sys.argv[2]
text = os.environ["INPUT_TEXT"]

print(token, chat_id, text)

bot = telegram.Bot(token=token)

bot.sendMessage(chat_id=chat_id,
                text=text,
                parse_mode='markdown',
                disable_web_page_preview=True)
