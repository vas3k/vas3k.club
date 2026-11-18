import openai
from django.conf import settings

from ai.config import OPENAI_CHAT_MODEL, REASONING_EFFORT

openai.api_key = settings.OPENAI_API_KEY


def create_response(**kwargs):
    request = openai.responses.parse if "text_format" in kwargs else openai.responses.create
    return request(
        model=OPENAI_CHAT_MODEL,
        reasoning={"effort": REASONING_EFFORT},
        truncation="auto",
        store=False,
        **kwargs,
    )
