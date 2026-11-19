import openai
from django.conf import settings

from ai.config import OPENAI_CHAT_MODEL, REASONING_EFFORT

openai.api_key = settings.OPENAI_API_KEY


def create_response(*, max_retries=None, **kwargs):
    kwargs.setdefault("timeout", 60)
    options = dict(
        model=OPENAI_CHAT_MODEL,
        reasoning={"effort": REASONING_EFFORT},
        truncation="disabled",
        store=False,
        **kwargs,
    )

    if max_retries is not None:
        with openai.OpenAI(api_key=settings.OPENAI_API_KEY, max_retries=max_retries) as client:
            request = client.responses.parse if "text_format" in kwargs else client.responses.create
            return request(**options)

    request = openai.responses.parse if "text_format" in kwargs else openai.responses.create
    return request(**options)
