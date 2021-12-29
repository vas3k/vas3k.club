import telegram
import os

token = os.environ["INPUT_BOT_TOKEN"]
chat_id = os.environ["INPUT_CHAT_ID"]
text = os.environ["INPUT_TEXT"]

bot = telegram.Bot(token=token)

bot.sendMessage(chat_id=chat_id,
                text=text,
                parse_mode='markdown',
                disable_web_page_preview=True)
