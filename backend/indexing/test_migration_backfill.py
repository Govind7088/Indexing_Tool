"""Purane (migration se pehle ke) data ko saaf karne wale backfill ka test."""
import importlib

from django.apps import apps
from django.test import TestCase

from .models import URLSubmission
from .url_utils import hash_url

migration = importlib.import_module('indexing.migrations.0003_backfill_url_hash_dedupe')


class BackfillTests(TestCase):

    def test_fills_hash_normalizes_and_merges_duplicates(self):
        a = URLSubmission.objects.create(url='https://example.com/a')
        b = URLSubmission.objects.create(url='https://other.com/b')
        c = URLSubmission.objects.create(url='https://third.com/c')
        # Purane data jaisa bigaado (update() save() ko bypass karta hai)
        URLSubmission.objects.filter(pk=a.pk).update(
            url='HTTPS://Example.com/a#top', url_hash='legacy-1')
        URLSubmission.objects.filter(pk=c.pk).update(
            url='https://example.com/a', url_hash='legacy-2')
        URLSubmission.objects.filter(pk=b.pk).update(url_hash='')

        migration.backfill_url_hash_and_merge_duplicates(apps, None)

        self.assertEqual(URLSubmission.objects.count(), 2)
        kept = URLSubmission.objects.get(pk=a.pk)  # sabse purana record bachta hai
        self.assertEqual(kept.url, 'https://example.com/a')
        self.assertEqual(kept.url_hash, hash_url('https://example.com/a'))
        self.assertFalse(URLSubmission.objects.filter(pk=c.pk).exists())
        self.assertEqual(URLSubmission.objects.get(pk=b.pk).url_hash,
                         hash_url('https://other.com/b'))

    def test_bare_domain_and_trailing_slash_are_merged(self):
        a = URLSubmission.objects.create(url='https://example.com')
        b = URLSubmission.objects.create(url='https://other.com')
        URLSubmission.objects.filter(pk=a.pk).update(url_hash='legacy-1')
        URLSubmission.objects.filter(pk=b.pk).update(
            url='HTTPS://Example.com/#top', url_hash='legacy-2')

        migration.backfill_url_hash_and_merge_duplicates(apps, None)

        self.assertEqual(URLSubmission.objects.count(), 1)
        self.assertEqual(URLSubmission.objects.get().pk, a.pk)