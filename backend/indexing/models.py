from django.db import models

from .url_utils import hash_url, normalize_url


class URLSubmission(models.Model):
    """Ek submit kiya hua URL (har URL ka sirf ek record)."""

    class InspectionStatus(models.TextChoices):
        NOT_INSPECTED = 'not_inspected', 'Not inspected'
        PENDING = 'pending', 'Pending'
        INDEXED = 'indexed', 'Indexed'
        NOT_INDEXED = 'not_indexed', 'Not indexed'
        QUOTA_EXCEEDED = 'quota_exceeded', 'Quota exceeded'
        AUTH_ERROR = 'auth_error', 'Google login problem'
        PERMISSION_DENIED = 'permission_denied', 'No access to this URL'
        ERROR = 'error', 'Error'

    class IndexingRequestStatus(models.TextChoices):
        NOT_REQUESTED = 'not_requested', 'Not requested'
        PENDING = 'pending', 'Pending'
        SUBMITTED = 'submitted', 'Submitted'
        FAILED = 'failed', 'Failed'

    # Lambe URL par unique index nahi ban sakta (MySQL utf8mb4, 3072 byte limit),
    # isliye uniqueness url_hash par hai.
    url = models.URLField(max_length=2048)
    url_hash = models.CharField(max_length=64, unique=True, editable=False)

    inspection_status = models.CharField(
        max_length=20,
        choices=InspectionStatus.choices,
        default=InspectionStatus.NOT_INSPECTED,
    )
    indexing_request_status = models.CharField(
        max_length=20,
        choices=IndexingRequestStatus.choices,
        default=IndexingRequestStatus.NOT_REQUESTED,
    )

    # Google ne jo coverage text bheja (jaise "URL is unknown to Google"), as-is.
    coverage_state = models.CharField(max_length=255, blank=True, default='')
    # Kab Google ne sach mein jawab diya (indexed/not_indexed). Error par set nahi hota.
    last_inspected_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ['-updated_at', '-id']  # sabse naya sabse pehle

    def __str__(self):
        return self.url

    def save(self, *args, **kwargs):
        self.url = normalize_url(self.url)
        self.url_hash = hash_url(self.url)
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            kwargs['update_fields'] = set(update_fields) | {'url', 'url_hash'}
        super().save(*args, **kwargs)

    @classmethod
    def submit(cls, raw_url):
        """URL save karo. Pehle se hai to wahi record update (updated_at) karo.

        Returns (record, created). get_or_create unique url_hash par chalta hai,
        isliye do requests ek saath aayein tab bhi duplicate record nahi banta.
        """
        url = normalize_url(raw_url)
        record, created = cls.objects.get_or_create(
            url_hash=hash_url(url), defaults={'url': url},
        )
        if not created:
            record.save(update_fields=['updated_at'])
        return record, created