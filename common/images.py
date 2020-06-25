import io
import logging
import os
from urllib.parse import urlparse

import requests
from PIL import Image
from django.conf import settings

log = logging.getLogger(__name__)


def upload_image_multipart(
    filename, data, resize=(192, 192), convert_to=None, quality=None
):
    if not data:
        return None

    if resize:
        try:
            image = Image.open(data)
        except Exception as ex:
            log.warning(f"Bad image data: {ex}")
            return None

        image.thumbnail(resize)
        saved_image = io.BytesIO()
        saved_image.name = filename

        try:
            image.save(saved_image)
        except OSError as ex:
            log.warning(f"Error saving image data: {ex}")
            return None

        data = saved_image.getvalue()

    upload_params = {
        "code": settings.MEDIA_UPLOAD_CODE
    }

    if convert_to:
        upload_params["convert_to"] = convert_to

    if quality:
        upload_params["quality"] = quality

    try:
        uploaded = requests.post(
            url=settings.MEDIA_UPLOAD_URL,
            params=upload_params,
            files={"media": (filename, data)},
            headers={"Accept": "application/json"},
        )
    except requests.exceptions.RequestException as ex:
        log.error(f"Image upload error: {ex}")
        return None

    if 200 <= uploaded.status_code <= 299:
        try:
            response_data = uploaded.json()
        except Exception as ex:
            log.error(f"Image upload error: {ex} ({uploaded.content})")
            return None

        return response_data["uploaded"][0]

    return None


def upload_image_from_url(url, resize=(192, 192), convert_to="jpg", quality=90):
    if settings.DEBUG or not settings.MEDIA_UPLOAD_URL or not settings.MEDIA_UPLOAD_CODE:
        return url

    if not url:
        return None

    image_name = os.path.basename(urlparse(url).path)
    if "." not in image_name:
        image_name += ".jpg"

    try:
        image_data = io.BytesIO(requests.get(url).content)
    except requests.exceptions.RequestException:
        return None

    return upload_image_multipart(image_name, image_data, resize=resize, convert_to=convert_to, quality=quality)
