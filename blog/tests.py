
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import RegistrationForm
from .models import Comment, Post
from .templatetags.blog_tags import markdown_format



User = get_user_model()


class BlogSecurityTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Test-Password-Only-For-Testing-123!'
        )

        self.post = Post.objects.create(
            title='Security Test Post',
            slug='security-test-post',
            author=self.user,
            body='Test content',
            status=Post.Status.PUBLISHED,
            publish=timezone.now() - timedelta(days=1)
        )

    def test_future_dated_post_is_not_public(self):
        future_post = Post.objects.create(
            title='Future Post',
            slug='future-post',
            author=self.user,
            body='This should not be public yet.',
            status=Post.Status.PUBLISHED,
            publish=timezone.now() + timedelta(days=1)
        )

        self.assertFalse(
            Post.published.filter(pk=future_post.pk).exists()
        )

    def test_future_dated_post_cannot_be_accessed_directly(self):
        future_post = Post.objects.create(
            title='Future Post',
            slug='future-post',
            author=self.user,
            body='This should remain private.',
            status=Post.Status.PUBLISHED,
            publish=timezone.now() + timedelta(days=1)
        )

        response = self.client.get(future_post.get_absolute_url())

        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_cannot_comment(self):
        url = reverse(
            'blog:post_comment',
            args=[self.post.pk]
        )

        response = self.client.post(
            url,
            {'body': 'Anonymous comment'}
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse('blog:register'),
            response['Location']
        )

        self.assertEqual(
            Comment.objects.filter(post=self.post).count(),
            0
        )

    def test_comment_endpoint_rejects_get_requests(self):
        url = reverse(
            'blog:post_comment',
            args=[self.post.pk]
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)

    def test_authenticated_user_can_comment(self):
        self.client.force_login(self.user)

        url = reverse(
            'blog:post_comment',
            args=[self.post.pk]
        )

        response = self.client.post(
            url,
            {'body': 'This is a valid comment.'}
        )

        self.assertEqual(response.status_code, 200)

        comment = Comment.objects.get(post=self.post)

        self.assertEqual(comment.name, self.user.username)
        self.assertEqual(comment.email, self.user.email)

    def test_overlong_comment_is_rejected(self):
        self.client.force_login(self.user)

        url = reverse(
            'blog:post_comment',
            args=[self.post.pk]
        )

        response = self.client.post(
            url,
            {'body': 'A' * 5001}
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Comment.objects.filter(post=self.post).count(),
            0
        )


class MarkdownSanitizationTests(SimpleTestCase):

    def test_normal_markdown_is_preserved(self):
        html = markdown_format("**Hello World**")

        self.assertIn(
            "<strong>Hello World</strong>",
            html
        )

    def test_script_injection_is_removed(self):
        html = markdown_format(
            '<script>alert("XSS")</script><p>Safe text</p>'
        )

        self.assertNotIn("<script", html.lower())
        self.assertNotIn("alert(", html.lower())
        self.assertIn("Safe text", html)

    def test_malicious_image_is_removed(self):
        html = markdown_format(
            '<img src=x onerror=alert(1)>'
        )

        self.assertNotIn("<img", html.lower())
        self.assertNotIn("onerror", html.lower())

    def test_javascript_url_is_removed(self):
        html = markdown_format(
            "[Click me](javascript:alert(1))"
        )

        self.assertNotIn(
            'href="javascript:',
            html.lower()
        )

        self.assertIn("Click me", html)

class RegistrationSecurityTests(TestCase):

    def setUp(self):
        self.existing_user = User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='Existing-Password-2026!'
        )

    def valid_registration_data(self):
        return {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'Violet-Piano-Window-Cloud-2026!',
            'password2': 'Violet-Piano-Window-Cloud-2026!',
        }

    def test_duplicate_email_is_rejected(self):
        data = self.valid_registration_data()
        data['email'] = 'existing@example.com'

        form = RegistrationForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_duplicate_email_case_insensitive(self):
        data = self.valid_registration_data()
        data['email'] = 'EXISTING@example.com'

        form = RegistrationForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_duplicate_username_is_rejected(self):
        data = self.valid_registration_data()
        data['username'] = 'existinguser'

        form = RegistrationForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_invalid_email_is_rejected(self):
        data = self.valid_registration_data()
        data['email'] = 'invalid-email'

        form = RegistrationForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_short_password_is_rejected(self):
        data = self.valid_registration_data()
        data['password1'] = 'short123'
        data['password2'] = 'short123'

        form = RegistrationForm(data=data)

        self.assertFalse(form.is_valid())

    def test_password_is_stored_as_hash(self):
        data = self.valid_registration_data()

        form = RegistrationForm(data=data)

        self.assertTrue(form.is_valid(), form.errors)

        user = form.save()

        self.assertTrue(
            user.check_password(data['password1'])
        )

        self.assertNotEqual(
            user.password,
            data['password1']
        )


class ExistingEndpointAuthorizationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='securityuser',
            email='security@example.com',
            password='Testing-Password-2026!'
        )

        self.post = Post.objects.create(
            title='Public Security Post',
            slug='public-security-post',
            author=self.user,
            body='Public content',
            status=Post.Status.PUBLISHED,
            publish=timezone.now() - timedelta(days=1)
        )

    def test_anonymous_user_cannot_share_post(self):
        url = reverse('blog:post_share', args=[self.post.pk])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)

        parsed_url = urlparse(response['Location'])
        query = parse_qs(parsed_url.query)

        self.assertEqual(
            parsed_url.path,
            reverse('blog:register')
        )
        self.assertEqual(query.get('action'), ['share'])

    def test_draft_post_is_not_publicly_accessible(self):
        draft = Post.objects.create(
            title='Private Draft',
            slug='private-draft',
            author=self.user,
            body='Private content',
            status=Post.Status.DRAFT,
            publish=timezone.now() - timedelta(days=1)
        )

        self.client.force_login(self.user)

        detail_response = self.client.get(
            draft.get_absolute_url()
        )

        share_response = self.client.get(
            reverse('blog:post_share', args=[draft.pk])
        )

        comment_response = self.client.post(
            reverse('blog:post_comment', args=[draft.pk]),
            {'body': 'Test comment'}
        )

        self.assertEqual(detail_response.status_code, 404)
        self.assertEqual(share_response.status_code, 404)
        self.assertEqual(comment_response.status_code, 404)

    def test_comment_without_csrf_token_is_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        response = csrf_client.post(
            reverse('blog:post_comment', args=[self.post.pk]),
            {'body': 'Comment without CSRF token'}
        )

        self.assertEqual(response.status_code, 403)

        self.assertFalse(
            Comment.objects.filter(post=self.post).exists()
        )

    def test_logout_get_request_is_rejected(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('logout'))

        self.assertEqual(response.status_code, 405)


class LoginSecurityTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='loginuser',
            email='login@example.com',
            password='Valid-Login-Password-2026!'
        )

    def test_valid_login_succeeds(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'loginuser',
                'password': 'Valid-Login-Password-2026!',
            }
        )

        self.assertRedirects(
            response,
            reverse('blog:post_list'),
            fetch_redirect_response=False
        )

        self.assertTrue(
            '_auth_user_id' in self.client.session
        )

    def test_external_next_redirect_is_rejected(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'loginuser',
                'password': 'Valid-Login-Password-2026!',
                'next': 'https://evil.example.com',
            }
        )

        self.assertRedirects(
            response,
            reverse('blog:post_list'),
            fetch_redirect_response=False
        )

    def test_login_rejects_request_without_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)

        response = csrf_client.post(
            reverse('login'),
            {
                'username': 'loginuser',
                'password': 'Valid-Login-Password-2026!',
            }
        )

        self.assertEqual(response.status_code, 403)


class PostOwnershipTests(TestCase):

    def setUp(self):
        self.user_a = User.objects.create_user(
            username='user_a',
            email='usera@example.com',
            password='User-A-Password-2026!'
        )

        self.user_b = User.objects.create_user(
            username='user_b',
            email='userb@example.com',
            password='User-B-Password-2026!'
        )

        self.post_a = Post.objects.create(
            title='User A Post',
            slug='user-a-post',
            author=self.user_a,
            body='Content written by User A',
            status=Post.Status.DRAFT,
            publish=timezone.now()
        )

    def test_anonymous_user_cannot_create_post(self):
        response = self.client.get(
            reverse('blog:post_create')
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Post.objects.count(), 1)

    def test_user_can_create_post_with_their_own_identity(self):
        self.client.force_login(self.user_b)

        response = self.client.post(
            reverse('blog:post_create'),
            {
                'title': 'My First Post',
                'body': 'This is my content.',
                'status': Post.Status.DRAFT,
                'tags': '',
                'author': self.user_a.pk,
            }
        )

        self.assertRedirects(
            response,
            reverse('blog:my_posts'),
            fetch_redirect_response=False
        )

        new_post = Post.objects.get(title='My First Post')

        self.assertEqual(new_post.author, self.user_b)
        self.assertNotEqual(new_post.author, self.user_a)
        self.assertTrue(new_post.slug)

    def test_users_only_see_their_own_posts(self):
        self.client.force_login(self.user_b)

        Post.objects.create(
            title='User B Post',
            slug='user-b-post',
            author=self.user_b,
            body='User B content',
            status=Post.Status.DRAFT,
            publish=timezone.now()
        )

        response = self.client.get(
            reverse('blog:my_posts')
        )

        self.assertEqual(response.status_code, 200)

        posts = list(response.context['posts'])

        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].author, self.user_b)

    def test_user_cannot_edit_another_users_post(self):
        self.client.force_login(self.user_b)

        response = self.client.get(
            reverse(
                'blog:post_edit',
                args=[self.post_a.pk]
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_delete_another_users_post(self):
        self.client.force_login(self.user_b)

        response = self.client.post(
            reverse(
                'blog:post_delete',
                args=[self.post_a.pk]
            )
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            Post.objects.filter(pk=self.post_a.pk).exists()
        )

    def test_get_request_does_not_delete_post(self):
        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse(
                'blog:post_delete',
                args=[self.post_a.pk]
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            Post.objects.filter(pk=self.post_a.pk).exists()
        )

    def test_owner_can_delete_their_own_post(self):
        self.client.force_login(self.user_a)

        response = self.client.post(
            reverse(
                'blog:post_delete',
                args=[self.post_a.pk]
            )
        )

        self.assertRedirects(
            response,
            reverse('blog:my_posts'),
            fetch_redirect_response=False
        )

        self.assertFalse(
            Post.objects.filter(pk=self.post_a.pk).exists()
        )

    def test_owner_can_edit_their_own_post(self):
        self.client.force_login(self.user_a)

        response = self.client.post(
            reverse(
                'blog:post_edit',
                args=[self.post_a.pk]
            ),
            {
                'title': 'Updated User A Post',
                'body': 'Updated content.',
                'status': Post.Status.DRAFT,
                'tags': '',
            }
        )


        self.assertRedirects(
            response,
            reverse('blog:my_posts'),
            fetch_redirect_response=False
        )

        self.post_a.refresh_from_db()

        self.assertEqual(
            self.post_a.title,
            'Updated User A Post'
        )

        self.assertEqual(self.post_a.author, self.user_a)
