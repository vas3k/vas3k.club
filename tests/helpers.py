from datetime import datetime, timedelta
import json
# from urllib.parse import urljoin
# import uuid

# import django
from django.test import Client
from django.urls import reverse
# from django.http.response import HttpResponseNotAllowed, HttpResponseBadRequest
# from django_q import brokers
# from django_q.signing import SignedPackage
# import jwt
# from unittest import skip
# from unittest.mock import patch
#
# django.setup()  # todo: how to run tests from PyCharm without this workaround?

from auth.models import Code, Session


# from auth.providers.common import Membership, Platform
# from auth.exceptions import PatreonException
# from tests.helpers import HelperClient
# from users.models.user import User


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
