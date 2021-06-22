import telegram
import os
import base64

token_base64 = os.environ["INPUT_TOKEN_B64"]
token = base64.b64decode(token_base64).decode()
text = os.environ["INPUT_TEXT"]
chat_id = os.environ["INPUT_CHAT_ID"]

bot = telegram.Bot(token=token)

bot.sendMessage(chat_id=chat_id,
                text=text,
                parse_mode='markdown',
                disable_web_page_preview=True)
