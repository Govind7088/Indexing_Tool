from urllib.parse import urlsplit

from rest_framework import serializers

from .models import URLSubmission
from .url_utils import normalize_url

ALLOWED_SCHEMES = ('http', 'https')


class URLSubmissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = URLSubmission
        fields = [
            'id', 'url', 'inspection_status', 'indexing_request_status', 'coverage_state', 'last_inspected_at',
            'created_at', 'updated_at',
        ]
        # Client in fields ko kabhi set nahi kar sakta (mass-assignment se bachav)
        read_only_fields = [
            'id', 'inspection_status', 'indexing_request_status', 'coverage_state', 'last_inspected_at',
            'created_at', 'updated_at',
        ]

    def validate_url(self, value):
        """Sirf http/https, credentials nahi, aur URL normalized shakal mein."""
        try:
            parts = urlsplit(value.strip())
        except ValueError:
            raise serializers.ValidationError('Valid URL do.')
        if parts.scheme.lower() not in ALLOWED_SCHEMES:
            raise serializers.ValidationError('Sirf http ya https URL allowed hai.')
        if '@' in parts.netloc:
            raise serializers.ValidationError(
                'URL mein username/password allowed nahi hai.')
        normalized = normalize_url(value)
        return normalized