from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .models import URLSubmission
from .serializers import URLSubmissionSerializer


class URLSubmissionCreateView(generics.CreateAPIView):
    """POST /api/urls/ -> URL save karo.

    Naya URL  -> 201 Created
    Pehle se hai -> 200 OK (wahi record update hota hai, naya nahi banta)
    """
    queryset = URLSubmission.objects.all()
    serializer_class = URLSubmissionSerializer
    # Spam/flood rokne ke liye rate limit (rate settings.py mein 'submit' ke naam se)
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'submit'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record, created = URLSubmission.submit(serializer.validated_data['url'])
        data = self.get_serializer(record).data
        return Response(
            data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class RecentURLListView(generics.ListAPIView):
    """GET /api/urls/recent/ -> sabse naye 5 URL."""
    serializer_class = URLSubmissionSerializer

    def get_queryset(self):
        return URLSubmission.objects.all()[:5]


class AllURLListView(generics.ListAPIView):
    """GET /api/urls/all/ -> saare URL."""
    queryset = URLSubmission.objects.all()
    serializer_class = URLSubmissionSerializer