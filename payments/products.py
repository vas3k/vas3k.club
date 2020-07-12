from django.conf import settings

PRODUCTS = {
    "club1": {
        "amount": 15,
        "description": "Членство в Клубе на год",
        "return_url": f"{settings.APP_HOST}/monies/done/",
    },
    "club3": {
        "amount": 40,
        "description": "Членство в Клубе на 3 года",
        "return_url": f"{settings.APP_HOST}/monies/done/",
    },
    "club50": {
        "amount": 150,
        "description": "Членство в Клубе на 50 лет",
        "return_url": f"{settings.APP_HOST}/monies/done/",
    },
}
