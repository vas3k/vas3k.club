import openai
from django.conf import settings

openai.api_key = settings.OPENAI_API_KEY

