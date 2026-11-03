from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import Comment



class EmailPostForm(forms.Form):
    to = forms.EmailField(label='Recipient email')
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea
    )


class CommentBoundField(forms.BoundField):
    comment_class = "comment"
    def css_classes(self, extra_classes=None):
        result = super().css_classes(extra_classes)
        if self.comment_class not in result:
            result += f" {self.comment_class}"
        return result.strip()


class CommentForm(forms.ModelForm):
    bound_field_class = CommentBoundField

    class Meta:
        model = Comment
        fields = ['body']

class SearchForm(forms.Form):
    query = forms.CharField()

class RegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = ['username', 'email']