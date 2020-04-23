from django import forms

from comments.models import Comment


class CommentForm(forms.ModelForm):
    text = forms.CharField(
        label="Текст комментария",
        required=True,
        max_length=10000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 10000,
                "placeholder": "Напишите комментарий...",
                "class": "markdown-editor-invisible",
            }
        ),
    )
    reply_to_id = forms.UUIDField(label="Ответ на", required=False)

    class Meta:
        model = Comment
        fields = ["text"]


# class ReplyForm(forms.ModelForm):
#     text = forms.CharField(
#         label="Ответ",
#         required=True,
#         max_length=10000,
#         widget=forms.Textarea(
#             attrs={
#                 "maxlength": 10000,
#                 "placeholder": "Напишите ответ...",
#             }
#         ),
#     )
#     reply_to_id = forms.UUIDField(label="Ответ на", required=True)
#
#     class Meta:
#         model = Comment
#         fields = ["text"]
