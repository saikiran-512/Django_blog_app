from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import Comment, Post



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

    body = forms.CharField(
        max_length=5000,
        widget=forms.Textarea
    )

    class Meta:
        model = Comment
        fields = ['body']

class SearchForm(forms.Form):
    query = forms.CharField(
        max_length=200,
        strip=True
    )

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, max_length=254)

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()

        if email and self._meta.model.objects.filter(
            email__iexact=email
        ).exists():
            raise forms.ValidationError(
                "An account with this Email address already exsists."
            )

        return email

    class Meta(UserCreationForm.Meta):
        fields = ['username', 'email']


class PostForm(forms.ModelForm):
    body = forms.CharField(
        max_length=50000,
        widget=forms.Textarea(attrs={'rows': 12})
    )

    class Meta:
        model = Post
        fields = ['title', 'body', 'tags', 'status']