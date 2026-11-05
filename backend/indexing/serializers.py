from urllib.parse import urlsplit

from rest_framework import serializers

from .models import URLSubmission

ALLOWED_SCHEMES = ('http', 'https')


class URLSubmissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = URLSubmission
        fields = ['id', 'url', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_url(self, value):
        """Sirf http/https allowed. ftp, javascript:, file: jaise schemes band."""
        if urlsplit(value).scheme.lower() not in ALLOWED_SCHEMES:
            raise serializers.ValidationError('Sirf http ya https URL allowed hai.')
        return value