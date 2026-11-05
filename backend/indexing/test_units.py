"""Unit tests: model aur serializer ko akele test karte hain."""
from django.test import TestCase

from .models import URLSubmission
from .serializers import URLSubmissionSerializer


class URLSubmissionModelTests(TestCase):

    def test_str_returns_url(self):
        item = URLSubmission.objects.create(url='https://example.com')
        self.assertEqual(str(item), 'https://example.com')

    def test_created_at_is_set_automatically(self):
        item = URLSubmission.objects.create(url='https://example.com')
        self.assertIsNotNone(item.created_at)

    def test_default_ordering_is_newest_first(self):
        first = URLSubmission.objects.create(url='https://first.com')
        second = URLSubmission.objects.create(url='https://second.com')
        self.assertEqual(list(URLSubmission.objects.all()), [second, first])


class URLSubmissionSerializerTests(TestCase):

    def test_valid_https_url(self):
        s = URLSubmissionSerializer(data={'url': 'https://example.com/page'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_valid_http_url(self):
        s = URLSubmissionSerializer(data={'url': 'http://example.com'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_rejects_plain_text(self):
        s = URLSubmissionSerializer(data={'url': 'not-a-valid-url'})
        self.assertFalse(s.is_valid())

    def test_rejects_empty_url(self):
        s = URLSubmissionSerializer(data={'url': ''})
        self.assertFalse(s.is_valid())

    def test_rejects_missing_url(self):
        s = URLSubmissionSerializer(data={})
        self.assertFalse(s.is_valid())

    def test_strips_surrounding_whitespace(self):
        s = URLSubmissionSerializer(data={'url': '  https://example.com  '})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data['url'], 'https://example.com')

    def test_rejects_ftp_scheme(self):
        s = URLSubmissionSerializer(data={'url': 'ftp://example.com/file'})
        self.assertFalse(s.is_valid())

    def test_rejects_url_longer_than_2048(self):
        long_url = 'https://example.com/' + 'a' * 2100
        s = URLSubmissionSerializer(data={'url': long_url})
        self.assertFalse(s.is_valid())

    def test_id_and_created_at_are_read_only(self):
        s = URLSubmissionSerializer(data={
            'url': 'https://example.com',
            'id': 999,
            'created_at': '2000-01-01T00:00:00Z',
        })
        self.assertTrue(s.is_valid(), s.errors)
        self.assertNotIn('id', s.validated_data)
        self.assertNotIn('created_at', s.validated_data)