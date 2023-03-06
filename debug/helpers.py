from datetime import datetime, timedelta
import json

from django.test import Client
from django.urls import reverse

from authn.models.session import Session


class JWT_STUB_VALUES:
    # using fully generated RS256 JWT Private Token because python jwt.encode implementation throws exception
    # with fake one or absent one
    JWT_PRIVATE_KEY_RS256 = """-----BEGIN RSA PRIVATE KEY-----
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
-----END RSA PRIVATE KEY-----"""
    JWT_PRIVATE_KEY = JWT_PRIVATE_KEY_RS256


class HelperClient(Client):

    def __init__(self, user=None):
        super(HelperClient, self).__init__()
        self.user = user

    def authorise(self):
        if not self.user:
            raise ValueError('Missed `user` property to use this method')

        session = Session.create_for_user(self.user)
        self.cookies["token"] = session.token
        self.cookies["token"]["expires"] = datetime.utcnow() + timedelta(days=30)
        self.cookies["token"]['httponly'] = True
        self.cookies["token"]['secure'] = True

        return self

    @staticmethod
    def is_response_contain(response, text):
        content = response.content
        if not isinstance(text, bytes):
            text = str(text)
            content = content.decode(response.charset)

        real_count = content.count(text)
        return real_count != 0

    def is_authorised(self) -> bool:
        response = self.get(reverse('debug_api_me'))
        content = response.content.decode(response.charset)
        content_dict = json.loads(content)

        return content_dict["is_authorised"]

    def print_me(self):
        response = self.get(reverse('debug_api_me'))
        content = response.content.decode(response.charset)
        content_dict = json.loads(content)

        return content_dict

    @staticmethod
    def is_access_denied(response):
        return HelperClient.is_response_contain(response, text="Эта страница доступна только участникам Клуба")
