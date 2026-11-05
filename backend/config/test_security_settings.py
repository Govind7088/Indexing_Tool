"""
Security settings tests (TDD - Step 1C).
Ye tests check karte hain ki settings.py secrets ko environment se padhe,
aur galat ya missing config par safe tareeke se fail ho (fail closed).
"""
import os
import runpy
from pathlib import Path
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

SETTINGS_PATH = Path(__file__).resolve().parent / 'settings.py'
VALID_KEY = 'test-key-' + 'x' * 60


def load_settings(env):
    """settings.py ko ek saaf (fake) environment ke saath run karta hai.
    Asli .env load na ho, isliye load_dotenv ko mock kar dete hain."""
    with mock.patch.dict(os.environ, env, clear=True), \
            mock.patch('dotenv.load_dotenv'):
        return runpy.run_path(str(SETTINGS_PATH))


class SecretKeyTests(SimpleTestCase):

    def test_secret_key_comes_from_environment(self):
        s = load_settings({'DJANGO_SECRET_KEY': VALID_KEY})
        self.assertEqual(s['SECRET_KEY'], VALID_KEY)

    def test_missing_secret_key_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            load_settings({})

    def test_short_secret_key_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            load_settings({'DJANGO_SECRET_KEY': 'short'})

    def test_placeholder_secret_key_raises(self):
        placeholder = 'change-me-' + 'x' * 60
        with self.assertRaises(ImproperlyConfigured):
            load_settings({'DJANGO_SECRET_KEY': placeholder})

    def test_no_hardcoded_insecure_key_in_source(self):
        source = SETTINGS_PATH.read_text(encoding='utf-8')
        self.assertNotIn('django-insecure', source)


class DebugTests(SimpleTestCase):

    def test_debug_defaults_to_false(self):
        s = load_settings({'DJANGO_SECRET_KEY': VALID_KEY})
        self.assertFalse(s['DEBUG'])

    def test_debug_true_when_explicit(self):
        s = load_settings({'DJANGO_SECRET_KEY': VALID_KEY,
                           'DJANGO_DEBUG': 'True'})
        self.assertTrue(s['DEBUG'])

    def test_debug_garbage_value_is_false(self):
        s = load_settings({'DJANGO_SECRET_KEY': VALID_KEY,
                           'DJANGO_DEBUG': 'banana'})
        self.assertFalse(s['DEBUG'])


class AllowedHostsTests(SimpleTestCase):

    def test_allowed_hosts_parsed_and_stripped(self):
        s = load_settings({'DJANGO_SECRET_KEY': VALID_KEY,
                           'DJANGO_ALLOWED_HOSTS': 'localhost, 127.0.0.1'})
        self.assertEqual(s['ALLOWED_HOSTS'], ['localhost', '127.0.0.1'])

    def test_allowed_hosts_default_is_empty(self):
        s = load_settings({'DJANGO_SECRET_KEY': VALID_KEY})
        self.assertEqual(s['ALLOWED_HOSTS'], [])