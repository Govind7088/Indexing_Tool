"""Recent/All list ordering tests.

Approved requirement: purana URL dobara submit karne par list mein sabse upar
aana chahiye (updated_at se), aur created_at nahi badalna chahiye.
"""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from .models import URLSubmission
from .testing import CleanAPITestCase


class ResubmitOrderingTests(CleanAPITestCase):

    def submit(self, url):
        return self.client.post(reverse('url-list'), {'url': url}, format='json')

    def urls(self, route_name):
        return [item['url'] for item in self.client.get(reverse(route_name)).data]

    def spread_timestamps(self, count):
        """Timestamps 1 minute ke gap par set karo (clock resolution par bharosa nahi)."""
        base = timezone.now() - timedelta(hours=1)
        for number, item in enumerate(URLSubmission.objects.order_by('id')[:count]):
            stamp = base + timedelta(minutes=number)
            URLSubmission.objects.filter(pk=item.pk).update(
                created_at=stamp, updated_at=stamp)

    def test_resubmitted_url_moves_to_top_of_recent(self):
        for n in range(3):
            self.submit(f'https://site{n}.com')
        self.spread_timestamps(3)

        again = self.submit('https://site0.com')

        self.assertEqual(again.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.urls('recent-urls'),
            ['https://site0.com', 'https://site2.com', 'https://site1.com'],
        )

    def test_resubmitted_url_moves_to_top_of_all(self):
        for n in range(3):
            self.submit(f'https://site{n}.com')
        self.spread_timestamps(3)

        self.submit('https://site1.com')

        self.assertEqual(
            self.urls('all-urls'),
            ['https://site1.com', 'https://site2.com', 'https://site0.com'],
        )

    def test_old_url_outside_top_five_returns_to_recent(self):
        for n in range(7):
            self.submit(f'https://site{n}.com')
        self.spread_timestamps(7)
        self.assertNotIn('https://site0.com', self.urls('recent-urls'))

        self.submit('https://site0.com')

        recent = self.urls('recent-urls')
        self.assertEqual(len(recent), 5)
        self.assertEqual(recent[0], 'https://site0.com')

    def test_resubmit_keeps_created_at(self):
        first = self.submit('https://example.com')
        item = URLSubmission.objects.get(pk=first.data['id'])
        old = timezone.now() - timedelta(days=2)
        URLSubmission.objects.filter(pk=item.pk).update(created_at=old)

        self.submit('https://example.com')

        item.refresh_from_db()
        self.assertEqual(item.created_at, old)
        self.assertGreater(item.updated_at, old)

    def test_same_timestamp_ties_are_broken_by_newest_id(self):
        for n in range(3):
            self.submit(f'https://site{n}.com')
        stamp = timezone.now() - timedelta(hours=1)
        URLSubmission.objects.update(created_at=stamp, updated_at=stamp)

        self.assertEqual(
            self.urls('all-urls'),
            ['https://site2.com', 'https://site1.com', 'https://site0.com'],
        )