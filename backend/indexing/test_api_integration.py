"""Integration tests: poora flow (HTTP -> view -> serializer -> MySQL)."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
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

    def test_new_submission_returns_default_statuses(self):
        response = self.submit('https://example.com')
        self.assertEqual(response.data['inspection_status'], 'not_inspected')
        self.assertEqual(response.data['indexing_request_status'], 'not_requested')

    def test_duplicate_url_returns_200_and_no_new_record(self):
        first = self.submit('https://example.com')
        second = self.submit('https://example.com')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data['id'], first.data['id'])
        self.assertEqual(URLSubmission.objects.count(), 1)

    def test_duplicate_url_updates_existing_record(self):
        first = self.submit('https://example.com')
        item = URLSubmission.objects.get(pk=first.data['id'])
        past = timezone.now() - timedelta(days=1)
        URLSubmission.objects.filter(pk=item.pk).update(updated_at=past)
        self.submit('https://example.com')
        item.refresh_from_db()
        self.assertGreater(item.updated_at, past)
        self.assertEqual(item.created_at, URLSubmission.objects.get().created_at)

    def test_duplicate_detection_ignores_host_case_and_fragment(self):
        self.submit('https://example.com/page')
        response = self.submit('HTTPS://EXAMPLE.com/page#top')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(URLSubmission.objects.count(), 1)

    def test_trailing_slash_on_bare_domain_is_same_url(self):
        first = self.submit('https://example.com')
        response = self.submit('https://example.com/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], first.data['id'])
        self.assertEqual(URLSubmission.objects.count(), 1)

    def test_path_case_makes_urls_different(self):
        self.submit('https://example.com/Page')
        response = self.submit('https://example.com/page')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(URLSubmission.objects.count(), 2)

    def test_different_query_makes_urls_different(self):
        self.submit('https://example.com/?a=1')
        response = self.submit('https://example.com/?a=2')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_duplicate_does_not_change_statuses(self):
        first = self.submit('https://example.com')
        URLSubmission.objects.filter(pk=first.data['id']).update(
            inspection_status='indexed', indexing_request_status='submitted')
        response = self.client.post(
            reverse('url-list'),
            {'url': 'https://example.com',
             'inspection_status': 'error', 'indexing_request_status': 'failed'},
            format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['inspection_status'], 'indexed')
        self.assertEqual(response.data['indexing_request_status'], 'submitted')

    def test_duplicate_appears_once_in_lists(self):
        self.submit('https://example.com')
        self.submit('https://example.com')
        self.assertEqual(len(self.client.get(reverse('recent-urls')).data), 1)
        self.assertEqual(len(self.client.get(reverse('all-urls')).data), 1)

    def test_lists_are_empty_when_no_data(self):
        self.assertEqual(self.client.get(reverse('recent-urls')).data, [])
        self.assertEqual(self.client.get(reverse('all-urls')).data, [])