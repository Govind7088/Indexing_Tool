from rest_framework import generics
from rest_framework.throttling import ScopedRateThrottle

from .models import URLSubmission
from .serializers import URLSubmissionSerializer


class URLSubmissionCreateView(generics.CreateAPIView):
    """POST /api/urls/ -> naya URL save karo."""
    queryset = URLSubmission.objects.all()
    serializer_class = URLSubmissionSerializer
    # Spam/flood rokne ke liye rate limit (rate settings.py mein 'submit' ke naam se)
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'submit'


class RecentURLListView(generics.ListAPIView):
    """GET /api/urls/recent/ -> sabse naye 5 URL."""
    serializer_class = URLSubmissionSerializer

    def get_queryset(self):
        return URLSubmission.objects.all()[:5]


class AllURLListView(generics.ListAPIView):
    """GET /api/urls/all/ -> saare URL."""
    queryset = URLSubmission.objects.all()
    serializer_class = URLSubmissionSerializer