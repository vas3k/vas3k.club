import requests
import os

url = "https://functions.yandexcloud.net/d4ej47q6ufr3qck629ti"
text = os.environ["INPUT_TEXT"]

requests.get(url, params={"text": text})
