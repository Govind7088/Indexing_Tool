from django.urls import reverse
from rest_framework import status

from .models import URLSubmission
from .testing import CleanAPITestCase


class URLSubmissionTests(CleanAPITestCase):

    def test_valid_url_submission(self):
        response = self.client.post(
            reverse('url-list'),
            {'url': 'https://example.com'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            URLSubmission.objects.filter(
                url='https://example.com'
            ).exists()
        )

    def test_invalid_url_submission(self):
        response = self.client.post(
            reverse('url-list'),
            {'url': 'not-a-valid-url'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recent_urls_returns_maximum_five(self):
        for number in range(7):
            URLSubmission.objects.create(
                url=f'https://example{number}.com'
            )

        response = self.client.get(reverse('recent-urls'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)

    def test_view_all_returns_all_urls(self):
        for number in range(7):
            URLSubmission.objects.create(
                url=f'https://example{number}.com'
            )

        response = self.client.get(reverse('all-urls'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 7)