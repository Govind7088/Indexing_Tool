"""Business logic: Google se status lo aur record mein save karo. Views patli rehti hain."""
from django.conf import settings
from django.utils import timezone

from . import google_client

ANSWERED = ('indexed', 'not_indexed')  # Google ne sach mein jawab diya

class URLNotAuthorized(Exception):
    """Aapke Google account ke paas is URL ki Search Console property par access nahi hai."""


def ensure_authorized(url):
    """Google ko koi inspection request jaane se PEHLE property access check.

    - Google band ho to kuch nahi karta.
    - Access nahi to URLNotAuthorized.
    - Google se property list hi na mile to GoogleAccessError (ye "unauthorized" nahi hai).
    """
    if not google_client.is_configured():
        return
    if google_client.find_property(url) is None:
        raise URLNotAuthorized(url)

def _inspect_and_store(record):
    result = google_client.inspect_url(record.url)
    record.inspection_status = result.status
    record.coverage_state = result.coverage_state
    if result.status in ANSWERED:
        record.last_inspected_at = timezone.now()
    return result


def refresh_status(record):
    """Sirf status poochho. updated_at nahi badalta, isliye list ki order nahi badalti."""
    if not google_client.is_configured():
        return record
    _inspect_and_store(record)
    record.save(update_fields=['inspection_status', 'coverage_state', 'last_inspected_at'])
    return record


def process_submission(record):
    """Submit par: status lo. Indexing request sirf tab jab enabled ho aur Google ne
    pakka bataya ho ki URL indexed nahi hai (error par kabhi nahi)."""
    if not google_client.is_configured():
        return record

    result = _inspect_and_store(record)
    fields = ['inspection_status', 'coverage_state', 'last_inspected_at']

    if settings.GOOGLE_INDEXING_API_ENABLED and result.status == 'not_indexed':
        record.indexing_request_status = google_client.request_indexing(record.url)
        fields.append('indexing_request_status')

    record.save(update_fields=fields)
    return record