from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase


@override_settings(
    GOOGLE_ENABLED=False,
    GOOGLE_INDEXING_API_ENABLED=False,
)
class CleanAPITestCase(APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()