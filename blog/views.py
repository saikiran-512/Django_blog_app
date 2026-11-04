from urllib.parse import urlencode
from taggit.models import Tag

from django.urls import reverse

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramWordSimilarity

from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify
from django.utils import timezone

from django.views.decorators.http import require_POST, require_http_methods
# from django.views.generic import ListView


from .forms import CommentForm, EmailPostForm, RegistrationForm, SearchForm, PostForm
from .models import Post

def generate_post_slug(title, publish_date, post=None):
    base_slug = slugify(title)[:240] or 'post'
    candidate = base_slug
    counter = 2

    while True:
        queryset = Post.objects.filter(
            slug=candidate,
            publish__date=publish_date.date()
        )

        if post is not None:
            queryset = queryset.exclude(pk=post.pk)

        if not queryset.exists():
            return candidate

        suffix = f'-{counter}'
        candidate = (
            f'{base_slug[:250 - len(suffix)].rstrip("-")}'
            f'{suffix}'
        )
        counter += 1

# Create your views here.
def post_list(request, tag_slug=None):
    post_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])
    # Pagination with 3 posts per page
    paginator = Paginator(post_list, 3)
    page_number = request.GET.get('page', 1)
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        #If page_number is not an integer get the first page
        posts = paginator.page(1)
    except EmptyPage:
        #If page_number is out of range get last page of results
        posts = paginator.page(paginator.num_pages)
    return render(
        request,
        'blog/post/list.html',
        {
            'posts': posts,
            'tag': tag
        }
    )

# Class-based view for post list
# class PostListView(ListView):
#     """
#     Alternative post list view
#     """
#     queryset = Post.published.all()
#     context_object_name = 'posts'
#     paginate_by = 3
#     template_name = 'blog/post/list.html'

def registration_redirect(action, next_url):
    query = urlencode({
        'action': action,
        'next': next_url
    })

    return redirect(f"{reverse('blog:register')}?{query}")

def post_detail(request, year, month, day, post):
    post = get_object_or_404(
        Post.published,
        slug=post,
        publish__year=year,
        publish__month=month,
        publish__day=day
    )

    # List of active comments for this post
    comments = post.comments.filter(active=True)

    # Form for users to comment
    form = CommentForm()

    # List of similar posts
    post_tags_ids = post.tags.values_list('id', flat=True)

    similar_posts = Post.published.filter(
        tags__in=post_tags_ids
    ).exclude(id=post.id)

    similar_posts = similar_posts.annotate(
        same_tags=Count('tags')
    ).order_by('-same_tags', '-publish')[:4]

    return render(
        request,
        'blog/post/detail.html',
        {
            'post' : post,
            'comments': comments,
            'form': form,
            'similar_posts': similar_posts
        }

    )


def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(
        Post.published,
        id=post_id,
    )
    if not request.user.is_authenticated:
        return registration_redirect(
            'share',
            request.get_full_path()
        )

    sent = False

    if request.method == 'POST':
        # Form was submitted
        form = EmailPostForm(request.POST)

        if form.is_valid():
            # Form fields passed validation
            cd = form.cleaned_data

            post_url = request.build_absolute_uri(
                post.get_absolute_url()
            )

            subject = (
                f"{request.user.username}"
                f"recommends you read {post.title}"
            )

            message = (
                f"Read {post.title} at {post_url}\n\n"
                f"Recommended by: {request.user.username}\n"
                f"Email: {request.user.email}\n\n"
                f"Comments: {cd['comments']}"
            )

            send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[cd['to']]
            )
            sent = True
    else:
        form = EmailPostForm()

    return render(
        request,
        'blog/post/share.html',
        {
            'post': post,
            'form': form,
            'sent': sent
        }
    )


@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(
        Post.published,
        id=post_id,
    )

    if not request.user.is_authenticated:
        return registration_redirect(
            'comment',
            post.get_absolute_url()
        )

    comment = None

    # A comment was posted
    form = CommentForm(data=request.POST)

    if form.is_valid():
        # Create Comment object without saving it to database
        comment = form.save(commit=False)

        # Assign the post to the comment
        comment.post = post

        # Assign the logged-in user's account details
        comment.name = request.user.username
        comment.email = request.user.email

        # Save the comment to the database
        comment.save()

    return render(
        request,
        'blog/post/comment.html',
        {
            'post': post,
            'form': form,
            'comment': comment
        }
    )

def post_search(request):
    form = SearchForm()
    query = None
    results = []

    if 'query' in request.GET:
        form = SearchForm(request.GET)

        if form.is_valid():
            query = form.cleaned_data['query']

            search_vector = (
                SearchVector('title', weight='A') +
                SearchVector('body', weight='B')
                )

            search_query = SearchQuery(query)

            results = (
                Post.published.annotate(
                    search=search_vector,
                    rank=SearchRank(search_vector, search_query),
                    title_similarity=TrigramWordSimilarity(query, 'title'),
                    body_similarity=TrigramWordSimilarity(query, 'body'),
                    )
                    .filter(
                        Q(rank__gte=0.3) |
                        Q(title_similarity__gt=0.3) |
                        Q(body_similarity__gt=0.3)
                    )
                    .order_by('-rank', '-title_similarity', '-body_similarity')
                )

    return render(
        request,
        'blog/post/search.html',
        {
            'form': form,
            'query': query,
            'results': results
        }
    )


def register(request):
    action = (
        request.GET.get('action')
        or request.POST.get('action', '')
    )

    next_url = (
        request.GET.get('next')
        or request.POST.get('next', '')
    )

    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)

            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return redirect(next_url)

            return redirect('blog:post_list')

    else:
        form = RegistrationForm()

    return render(
        request,
        'registration/register.html',
        {
            'form': form,
            'action': action,
            'next': next_url
        }
    )


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST)

        if form.is_valid():
            post = form.save(commit=False)

            # Assign the logged-in user as author.
            post.author = request.user

            # New posts receive the current publication timestamp.
            post.publish = timezone.now()

            post.slug = generate_post_slug(
                post.title,
                post.publish
            )

            post.save()
            form.save_m2m()

            return redirect('blog:my_posts')

    else:
        form = PostForm()

    return render(
        request,
        'blog/post/post_form.html',
        {'form': form, 'title': 'Create a post'}
    )


@login_required
def my_posts(request):
    posts = Post.objects.filter(
        author=request.user
    ).order_by('-updated')

    return render(
        request,
        'blog/post/my_posts.html',
        {'posts': posts}
    )


@login_required
def post_edit(request, post_id):
    # Only the owner can retrieve this post for editing.
    post = get_object_or_404(
        Post,
        pk=post_id,
        author=request.user
    )

    old_status = post.status
    old_title = post.title

    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)

        if form.is_valid():
            post = form.save(commit=False)

            # Reset publication date when publishing a draft.
            if (
                old_status == Post.Status.DRAFT
                and post.status == Post.Status.PUBLISHED
            ):
                post.publish = timezone.now()

                post.slug = generate_post_slug(
                    post.title,
                    post.publish,
                    post=post
                )

            # Update the slug when editing a draft title.
            elif (
                post.status == Post.Status.DRAFT
                and old_title != post.title
            ):
                post.slug = generate_post_slug(
                    post.title,
                    post.publish,
                    post=post
                )

            post.save()
            form.save_m2m()

            return redirect('blog:my_posts')

    else:
        form = PostForm(instance=post)

    return render(
        request,
        'blog/post/post_form.html',
        {
            'form': form,
            'title': 'Edit post',
            'post': post
        }
    )


@login_required
@require_http_methods(["GET", "POST"])
def post_delete(request, post_id):
    # Return 404 if the post doesn't belong to this user.
    post = get_object_or_404(
        Post,
        pk=post_id,
        author=request.user
    )

    if request.method == 'POST':
        post.delete()
        return redirect('blog:my_posts')

    return render(
        request,
        'blog/post/post_confirm_delete.html',
        {'post': post}
    )
