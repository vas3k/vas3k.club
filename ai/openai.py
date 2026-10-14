import openai
from django.conf import settings

from ai.config import OPENAI_CHAT_MODEL, REASONING_EFFORT

openai.api_key = settings.OPENAI_API_KEY


def create_response(**kwargs):
    return openai.responses.create(
        model=OPENAI_CHAT_MODEL,
        reasoning={"effort": REASONING_EFFORT},
        truncation="auto",
        store=False,
        **kwargs,
    )
