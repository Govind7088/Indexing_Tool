from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .models import URLSubmission
from .serializers import URLSubmissionSerializer

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from . import google_client
from .services import process_submission, refresh_status
from .services import (URLNotAuthorized, ensure_authorized, process_submission, refresh_status)

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
        serializer.is_valid(raise_exception=True)  # 1) sirf URL ki shakal
        url = serializer.validated_data['url']
        try:
            ensure_authorized(url)  # 2) property access, Google inspection se PEHLE
        except URLNotAuthorized:
            return Response(
                {'url': ['Is URL ke liye aapke Google account ke paas Search Console access nahi hai.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except google_client.GoogleAccessError:
            # Google se property check hi nahi ho payi: kuch save nahi hota, details bahar nahi jaati.
            return Response(
                {'detail': 'Google is not available right now.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        record, created = URLSubmission.submit(url)  # 3) save
        record = process_submission(record)          # 4) Google inspection
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
    
class URLRecheckView(APIView):
    """POST /api/urls/<id>/recheck/ -> Google se status dobara poochho (naya indexing request nahi)."""
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'recheck'

    def post(self, request, pk):
        if not google_client.is_configured():
            return Response({'detail': 'Google is not configured.'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        record = get_object_or_404(URLSubmission, pk=pk)
        record = refresh_status(record)
        return Response(URLSubmissionSerializer(record).data)