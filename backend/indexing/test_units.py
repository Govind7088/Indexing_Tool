"""Unit tests: URL helpers, model aur serializer ko akele test karte hain."""
import hashlib
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from .models import URLSubmission
from .serializers import URLSubmissionSerializer
from .url_utils import hash_url, normalize_url


class NormalizeUrlTests(SimpleTestCase):

    def test_lowercases_scheme_and_host(self):
        self.assertEqual(normalize_url('HTTPS://Example.COM/Path'),
                         'https://example.com/Path')

    def test_keeps_path_case_and_query(self):
        self.assertEqual(normalize_url('https://example.com/A/b?X=1&y=Z'),
                         'https://example.com/A/b?X=1&y=Z')

    def test_removes_fragment(self):
        self.assertEqual(normalize_url('https://example.com/a#section'),
                         'https://example.com/a')

    def test_strips_whitespace(self):
        self.assertEqual(normalize_url('  https://example.com  '),
                         'https://example.com')

    def test_does_not_add_trailing_slash(self):
        self.assertEqual(normalize_url('https://example.com'),
                         'https://example.com')

    def test_keeps_port(self):
        self.assertEqual(normalize_url('https://Example.com:8443/x'),
                         'https://example.com:8443/x')


class HashUrlTests(SimpleTestCase):

    def test_is_sha256_hex_of_normalized_url(self):
        expected = hashlib.sha256(b'https://example.com/a').hexdigest()
        self.assertEqual(hash_url('HTTPS://Example.com/a#frag'), expected)

    def test_empty_path_and_slash_have_same_hash(self):
        self.assertEqual(hash_url('https://example.com'),
                         hash_url('https://example.com/'))
        self.assertEqual(hash_url('https://example.com?a=1'),
                         hash_url('https://example.com/?a=1'))

    def test_length_is_64(self):
        self.assertEqual(len(hash_url('https://example.com')), 64)

    def test_different_urls_have_different_hashes(self):
        self.assertNotEqual(hash_url('https://a.com'), hash_url('https://b.com'))


class URLSubmissionModelTests(TestCase):

    def test_str_returns_url(self):
        item = URLSubmission.objects.create(url='https://example.com')
        self.assertEqual(str(item), 'https://example.com')

    def test_created_and_updated_at_are_set_automatically(self):
        item = URLSubmission.objects.create(url='https://example.com')
        self.assertIsNotNone(item.created_at)
        self.assertIsNotNone(item.updated_at)

    def test_default_ordering_is_newest_first(self):
        first = URLSubmission.objects.create(url='https://first.com')
        second = URLSubmission.objects.create(url='https://second.com')
        self.assertEqual(list(URLSubmission.objects.all()), [second, first])

    def test_status_defaults(self):
        item = URLSubmission.objects.create(url='https://example.com')
        self.assertEqual(item.inspection_status, 'not_inspected')
        self.assertEqual(item.indexing_request_status, 'not_requested')

    def test_status_choices_are_frozen(self):
        self.assertEqual(
            URLSubmission.InspectionStatus.values,
            ['not_inspected', 'pending', 'indexed', 'not_indexed',
            'quota_exceeded', 'auth_error', 'permission_denied', 'error'])
        self.assertEqual(
            URLSubmission.IndexingRequestStatus.values,
            ['not_requested', 'pending', 'submitted', 'failed'])

    def test_invalid_status_value_fails_validation(self):
        item = URLSubmission.objects.create(url='https://example.com')
        item.inspection_status = 'hacked'
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_url_hash_is_set_on_save(self):
        item = URLSubmission.objects.create(url='https://example.com/a')
        self.assertEqual(item.url_hash, hash_url('https://example.com/a'))

    def test_save_normalizes_url(self):
        item = URLSubmission.objects.create(url='HTTPS://Example.com/a#x')
        self.assertEqual(item.url, 'https://example.com/a')

    def test_database_blocks_duplicate_even_with_different_case(self):
        URLSubmission.objects.create(url='https://example.com/a')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                URLSubmission.objects.create(url='HTTPS://EXAMPLE.COM/a')
        self.assertEqual(URLSubmission.objects.count(), 1)

    def test_submit_creates_then_reuses(self):
        first, created_first = URLSubmission.submit('https://example.com')
        second, created_second = URLSubmission.submit('HTTPS://example.com#x')
        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(URLSubmission.objects.count(), 1)

    def test_submit_on_duplicate_touches_updated_at_only(self):
        item, _ = URLSubmission.submit('https://example.com')
        past = timezone.now() - timedelta(days=1)
        URLSubmission.objects.filter(pk=item.pk).update(
            updated_at=past, inspection_status='indexed')
        again, created = URLSubmission.submit('https://example.com')
        again.refresh_from_db()
        self.assertFalse(created)
        self.assertGreater(again.updated_at, past)
        self.assertEqual(again.created_at, item.created_at)
        self.assertEqual(again.inspection_status, 'indexed')


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

    def test_returns_normalized_url(self):
        s = URLSubmissionSerializer(data={'url': 'HTTPS://Example.com/a#x'})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data['url'], 'https://example.com/a')

    def test_rejects_ftp_scheme(self):
        s = URLSubmissionSerializer(data={'url': 'ftp://example.com/file'})
        self.assertFalse(s.is_valid())

    def test_rejects_credentials_in_url(self):
        s = URLSubmissionSerializer(data={'url': 'https://user:secret@example.com'})
        self.assertFalse(s.is_valid())

    def test_rejects_url_longer_than_2048(self):
        long_url = 'https://example.com/' + 'a' * 2100
        s = URLSubmissionSerializer(data={'url': long_url})
        self.assertFalse(s.is_valid())

    def test_server_controlled_fields_are_read_only(self):
        s = URLSubmissionSerializer(data={
            'url': 'https://example.com',
            'id': 999,
            'created_at': '2000-01-01T00:00:00Z',
            'updated_at': '2000-01-01T00:00:00Z',
            'inspection_status': 'indexed',
            'indexing_request_status': 'submitted',
        })
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(list(s.validated_data.keys()), ['url'])

    def test_output_fields(self):
        item = URLSubmission.objects.create(url='https://example.com')
        self.assertEqual(
            set(URLSubmissionSerializer(item).data.keys()),
            {'id', 'url', 'inspection_status', 'indexing_request_status',
             'coverage_state', 'last_inspected_at', 'created_at', 'updated_at'})