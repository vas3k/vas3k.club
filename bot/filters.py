from telegram import Message
from telegram.ext import filters

from bot.config import COMMENT_EMOJI_RE, POST_EMOJI_RE


class ReplyToBot(filters.MessageFilter):
    def filter(self, message: Message) -> bool:
        reply = message.reply_to_message
        return bool(reply and reply.from_user and reply.from_user.id == message.get_bot().id)


class ReplyToClubContent(filters.MessageFilter):
    def filter(self, message: Message) -> bool:
        reply = message.reply_to_message

        if not reply:
            return False

        text = (reply.text or reply.caption or "")[:10]
        return bool(COMMENT_EMOJI_RE.match(text) or POST_EMOJI_RE.match(text))
