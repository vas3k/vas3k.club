from django import forms
from django.core.exceptions import ValidationError

from comments.models import Comment
from posts.models.post import Post


class CommentForm(forms.ModelForm):
    text = forms.CharField(
        label="Текст комментария",
        required=True,
        max_length=20000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 20000,
                "placeholder": "Напишите комментарий...",
                "class": "markdown-editor-invisible",
            }
        ),
    )
    subscribe_to_post = forms.BooleanField(
        label="подписаться на комментарии",
        label_suffix="",
        initial=True,
        required=False,
    )

    class Meta:
        model = Comment
        fields = ["text"]


class ReplyForm(forms.ModelForm):
    text = forms.CharField(
        label="Ответ",
        required=True,
        max_length=20000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 20000,
                "placeholder": "Напишите ответ...",
                "class": "markdown-editor-invisible",
            }
        ),
    )
    reply_to_id = forms.UUIDField(label="Ответ на", required=True)

    class Meta:
        model = Comment
        fields = [
            "text",
            # "reply_to",
        ]

    def clean(self):
        cleaned_data = super().clean()

        try:
            self.instance.reply_to = Comment.objects.get(id=cleaned_data["reply_to_id"])
        except Comment.DoesNotExist:
            raise ValidationError("Ответ на неизвестный коммент")

        return cleaned_data


class BattleCommentForm(forms.ModelForm):
    battle_side = forms.ChoiceField(
        label="На чьей вы стороне?",
        required=True,
        choices=[("a", "A"), ("b", "B")],
    )
    title = forms.CharField(
        label="Кратко",
        required=True,
        max_length=128,
        widget=forms.TextInput(attrs={
            "maxlength": 128,
            "placeholder": "Кратко ваш аргумент почему",
        })
    )
    text = forms.CharField(
        label="Развернутая мысль",
        required=True,
        max_length=20000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 20000,
                "placeholder": "Развернутый ответ...",
                "class": "markdown-editor-invisible",
            }
        ),
    )
    subscribe_to_post = forms.BooleanField(
        label="подписаться на комментарии",
        label_suffix="",
        initial=True,
        required=False,
    )

    class Meta:
        model = Comment
        fields = [
            "title",
            "text"
        ]

    def clean(self):
        cleaned_data = super().clean()
        self.instance.metadata = {
            "battle": {
                "side": cleaned_data["battle_side"]
            }
        }
        return cleaned_data


def edit_form_class_for_comment(comment):
    if comment.reply_to:
        return ReplyForm
    elif comment.post.type == Post.TYPE_BATTLE:
        return BattleCommentForm
    else:
        return CommentForm
