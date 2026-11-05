from django.core.cache import cache
from rest_framework.test import APITestCase


class CleanAPITestCase(APITestCase):
    """Har test se pehle cache saaf karta hai.

    Throttling (rate limit) ka counter cache mein rehta hai. Cache saaf na ho
    to ek test ke requests dusre test ko 429 (Too Many Requests) dilwa sakte hain.
    """

    def setUp(self):
        super().setUp()
        cache.clear()