"""Integration tests: poora flow (HTTP -> view -> serializer -> MySQL)."""
from django.urls import reverse
from rest_framework import status

from .models import URLSubmission
from .testing import CleanAPITestCase


class SubmitThenListFlowTests(CleanAPITestCase):

    def submit(self, url):
        return self.client.post(reverse('url-list'), {'url': url}, format='json')

    def test_post_response_contains_saved_data(self):
        response = self.submit('https://example.com')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['url'], 'https://example.com')
        self.assertIn('id', response.data)
        self.assertIn('created_at', response.data)

    def test_full_flow_recent_shows_newest_first(self):
        for n in range(7):
            self.assertEqual(
                self.submit(f'https://site{n}.com').status_code,
                status.HTTP_201_CREATED,
            )
        recent = self.client.get(reverse('recent-urls'))
        urls = [item['url'] for item in recent.data]
        self.assertEqual(urls, [f'https://site{n}.com' for n in (6, 5, 4, 3, 2)])

    def test_full_flow_all_returns_everything(self):
        for n in range(7):
            self.submit(f'https://site{n}.com')
        response = self.client.get(reverse('all-urls'))
        self.assertEqual(len(response.data), 7)

    def test_invalid_submission_is_not_saved(self):
        self.submit('not-a-valid-url')
        self.assertEqual(URLSubmission.objects.count(), 0)

    def test_duplicate_urls_are_allowed(self):
        self.submit('https://example.com')
        self.submit('https://example.com')
        self.assertEqual(URLSubmission.objects.count(), 2)

    def test_lists_are_empty_when_no_data(self):
        self.assertEqual(self.client.get(reverse('recent-urls')).data, [])
        self.assertEqual(self.client.get(reverse('all-urls')).data, [])