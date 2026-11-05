"""Security / pen-test tests: attacker ki tarah API par hamle."""
from django.urls import reverse
from rest_framework import status

from .models import URLSubmission
from .testing import CleanAPITestCase


class MaliciousInputTests(CleanAPITestCase):

    def post(self, payload):
        return self.client.post(reverse('url-list'), payload, format='json')

    def test_dangerous_schemes_are_rejected(self):
        for bad in ('javascript:alert(1)', 'data:text/html,<script>alert(1)</script>',
                    'file:///etc/passwd', 'ftp://example.com/x', 'vbscript:msgbox(1)'):
            with self.subTest(url=bad):
                self.assertEqual(self.post({'url': bad}).status_code,
                                 status.HTTP_400_BAD_REQUEST)
        self.assertEqual(URLSubmission.objects.count(), 0)

    def test_oversized_url_is_rejected(self):
        response = self.post({'url': 'https://example.com/' + 'a' * 5000})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_types_are_rejected_not_crashing(self):
        for bad in (123, None, ['https://a.com'], {'x': 1}, True):
            with self.subTest(value=bad):
                self.assertEqual(self.post({'url': bad}).status_code,
                                 status.HTTP_400_BAD_REQUEST)

    def test_json_list_body_is_rejected(self):
        self.assertEqual(self.post(['https://example.com']).status_code,
                         status.HTTP_400_BAD_REQUEST)

    def test_broken_json_is_rejected(self):
        response = self.client.post(reverse('url-list'), data='{"url": ',
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mass_assignment_is_ignored(self):
        response = self.post({'url': 'https://example.com', 'id': 999,
                              'created_at': '2000-01-01T00:00:00Z'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(response.data['id'], 999)
        self.assertNotIn('2000-01-01', response.data['created_at'])

    def test_sql_injection_payload_is_stored_as_plain_data(self):
        payload = "https://example.com/?id=1'%20OR%20'1'='1"
        self.assertEqual(self.post({'url': payload}).status_code,
                         status.HTTP_201_CREATED)
        self.assertEqual(URLSubmission.objects.get().url, payload)
        # table abhi bhi safe hai
        self.assertEqual(URLSubmission.objects.count(), 1)

    def test_script_in_url_never_comes_back_as_html(self):
        payload = 'https://example.com/<script>alert(1)</script>'
        self.post({'url': payload})
        response = self.client.get(reverse('recent-urls'),
                                   HTTP_ACCEPT='text/html,*/*;q=0.8')
        self.assertTrue(response['Content-Type'].startswith('application/json'))
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')


class MethodAndExposureTests(CleanAPITestCase):

    def test_write_methods_not_allowed_on_list_endpoints(self):
        for name in ('recent-urls', 'all-urls'):
            for method in ('post', 'put', 'patch', 'delete'):
                with self.subTest(endpoint=name, method=method):
                    response = getattr(self.client, method)(reverse(name))
                    self.assertEqual(response.status_code,
                                     status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_cannot_update_or_delete_on_submit_endpoint(self):
        for method in ('put', 'patch', 'delete'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(reverse('url-list'))
                self.assertEqual(response.status_code,
                                 status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_admin_requires_login(self):
        for path in ('/admin/', '/admin/indexing/urlsubmission/'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/admin/login/', response['Location'])


class RateLimitTests(CleanAPITestCase):

    def test_flooding_submit_endpoint_gets_throttled(self):
        statuses = []
        for n in range(30):
            response = self.client.post(reverse('url-list'),
                                        {'url': f'https://flood{n}.com'},
                                        format='json')
            statuses.append(response.status_code)
        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, statuses)
        self.assertLess(URLSubmission.objects.count(), 30)