import io

from django import forms

from common.images import upload_image_multipart


class ImageUploadField(forms.ImageField):
    def __init__(self, resize=None, convert_to=None, quality=None, **kwargs):
        super().__init__(**kwargs)
        self.resize = resize
        self.convert_to = convert_to
        self.quality = int(quality or 90)

    def clean(self, data, initial=None):
        if not data:
            return initial

        return upload_image_multipart(
            filename=data.name,
            data=io.BytesIO(data.read()),
            resize=self.resize,
            convert_to=self.convert_to,
            quality=self.quality,
        )


class DefaultSelect(forms.Select):
    DEFAULT_CLASS = 'select'

    def __init__(self):
        super().__init__(attrs={'class': self.DEFAULT_CLASS})


class DefaultChoiceField(forms.ChoiceField):
    def __init__(self, widget=None, **kwargs):
        self.widget = DefaultSelect()
        super().__init__(**kwargs)

class DefaultModelChoiceField(forms.ModelChoiceField):
    def __init__(self, widget=None, **kwargs):
        self.widget = DefaultSelect()
        super().__init__(**kwargs)
