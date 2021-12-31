import requests
import os

url = "https://functions.yandexcloud.net/d4ecdlucu902ufaqjpea"
text = os.environ["INPUT_TEXT"]

requests.get(url, params={"text": text})
