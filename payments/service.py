import Adyen
from django.conf import settings

ady = Adyen.Adyen()

ady.payment.client.merchant_account = settings.ADYEN_MERCHANT_ACCOUNT
ady.payment.client.platform = settings.ADYEN_PLATFORM
ady.payment.client.xapikey = settings.ADYEN_API_KEY
ady.payment.client.hmac = settings.ADYEN_HMAC
