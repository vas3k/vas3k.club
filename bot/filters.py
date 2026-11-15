from telegram import Message
from telegram.ext import filters


class ReplyToBot(filters.MessageFilter):
    def filter(self, message: Message) -> bool:
        reply = message.reply_to_message
        return bool(reply and reply.from_user and reply.from_user.id == message.get_bot().id)
