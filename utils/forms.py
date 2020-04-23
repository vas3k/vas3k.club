import io

from django import forms

from utils.images import upload_image_bytes


class ImageUploadField(forms.ImageField):
    def __init__(self, resize=None, convert_format="JPEG", **kwargs):
        super().__init__(**kwargs)
        self.resize = resize
        self.convert_format = convert_format

    def clean(self, data, initial=None):
        if not data:
            return initial

        return upload_image_bytes(
            filename=data.name,
            data=io.BytesIO(data.read()),
            resize=self.resize,
            convert_format=self.convert_format,
            quality=90,
        )
