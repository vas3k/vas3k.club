import Adyen
from django.conf import settings

ady = Adyen.Adyen()

ady.payment.client.platform = settings.ADYEN_PLATFORM
ady.payment.client.xapikey = settings.ADYEN_API_KEY
