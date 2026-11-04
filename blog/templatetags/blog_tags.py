from django import template
from django.db.models import Count
from django.utils.safestring import mark_safe
from ..models import Post
import markdown
import nh3

register = template.Library()

@register.simple_tag
def total_posts():
    return Post.published.count()

@register.inclusion_tag('blog/post/latest_posts.html')
def show_latest_posts(count=5):
    latest_posts = Post.published.order_by('-publish')[:count]
    return {'latest_posts': latest_posts}

@register.simple_tag
def get_most_commented_posts(count=5):
    return Post.published.annotate(
        total_comments=Count('comments')
    ).order_by('-total_comments')[:count]


# Allow only safe HTML generated from Markdown
MARKDOWN_CLEANER = nh3.Cleaner(
    tags={
        'a', 'blockquote', 'br', 'code',
        'em', 'strong',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'hr', 'li', 'ol', 'p', 'pre', 'ul',
    },
    attributes={
        'a': {'href', 'title'},
    },
    clean_content_tags={
        'script', 'style', 'iframe', 'object', 'embed',
    },
    url_schemes={'http', 'https', 'mailto'},
)

@register.filter(name='markdown')
def markdown_format(text):
    if not text:
        return ''

    html = markdown.markdown(text)
    clean_html = MARKDOWN_CLEANER.clean(html)

    return mark_safe(clean_html)