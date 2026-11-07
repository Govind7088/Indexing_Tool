"""Google se baat karne wala akela module. Baaki app Google ke baare mein kuch nahi jaanti.

Login: Application Default Credentials (ADC) ya optional service account.
Token kabhi log/response mein nahi jata.
"""
import logging
import time
from collections import namedtuple
from urllib.parse import urlsplit

import google.auth
from django.conf import settings
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

TIMEOUT = 15  # seconds
SITES_URL = 'https://www.googleapis.com/webmasters/v3/sites'
INSPECT_URL = 'https://searchconsole.googleapis.com/v1/urlInspection/index:inspect'
PUBLISH_URL = 'https://indexing.googleapis.com/v3/urlNotifications:publish'
SCOPE_SEARCH_CONSOLE = 'https://www.googleapis.com/auth/webmasters.readonly'
SCOPE_INDEXING = 'https://www.googleapis.com/auth/indexing'
PROPERTIES_TTL = 300  # seconds
COVERAGE_MAX = 255
# Inspection ke liye in permission levels ki property chalti hai ('siteUnverifiedUser' nahi).
USABLE_PERMISSIONS = {'siteOwner', 'siteFullUser', 'siteRestrictedUser'}

InspectionResult = namedtuple('InspectionResult', ['status', 'coverage_state'])

_session = None
_properties_cache = None  # (time, entries)


class GoogleAccessError(Exception):
    """Google tak pahunch nahi paye. .status: auth_error / quota_exceeded / permission_denied / error."""

    def __init__(self, status):
        super().__init__(status)
        self.status = status


def is_configured():
    return settings.GOOGLE_ENABLED


def clear_cache():
    global _session, _properties_cache
    _session = None
    _properties_cache = None


def _status_for_http(code):
    return {401: 'auth_error', 403: 'permission_denied', 429: 'quota_exceeded'}.get(code, 'error')


def _status_for_exception(exc):
    # Login/credentials ki problem alag hai, network/timeout ki alag.
    return 'auth_error' if isinstance(exc, GoogleAuthError) else 'error'


def _get_session():
    global _session
    if _session is None:
        scopes = [SCOPE_SEARCH_CONSOLE]
        if settings.GOOGLE_INDEXING_API_ENABLED:
            scopes.append(SCOPE_INDEXING)
        if settings.GOOGLE_SERVICE_ACCOUNT_FILE:
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=scopes)
        else:
            credentials, _ = google.auth.default(scopes=scopes)  # ADC
        if settings.GOOGLE_CLOUD_PROJECT:
            credentials = credentials.with_quota_project(settings.GOOGLE_CLOUD_PROJECT)
        _session = AuthorizedSession(credentials)
    return _session


def list_properties():
    """Aapke Google account ki Search Console properties (5 minute cache)."""
    global _properties_cache
    if _properties_cache and time.monotonic() - _properties_cache[0] < PROPERTIES_TTL:
        return _properties_cache[1]
    try:
        response = _get_session().get(SITES_URL, timeout=TIMEOUT)
        if response.status_code != 200:
            logger.warning('Listing properties failed: HTTP %s', response.status_code)
            raise GoogleAccessError(_status_for_http(response.status_code))
        entries = response.json().get('siteEntry', [])
    except GoogleAccessError:
        raise
    except Exception as exc:  # message log nahi karte (secret ho sakta hai)
        logger.warning('Listing properties error: %s', type(exc).__name__)
        raise GoogleAccessError(_status_for_exception(exc))
    _properties_cache = (time.monotonic(), entries)
    return entries


def _match_length(site, url):
    """URL us property ka ho to match ki lambai (bada = zyada specific), warna 0."""
    if site.startswith('sc-domain:'):
        domain = site[len('sc-domain:'):].lower()
        host = (urlsplit(url).hostname or '').lower()
        return len(domain) if host == domain or host.endswith('.' + domain) else 0
    return len(site) if url.startswith(site) else 0


def find_property(url):
    """Us property ka naam jo is URL ko cover karti hai aur jis par access hai, warna None."""
    best, best_len = None, 0
    for entry in list_properties():
        if entry.get('permissionLevel') not in USABLE_PERMISSIONS:
            continue
        site = entry.get('siteUrl', '')
        length = _match_length(site, url)
        if length > best_len:
            best, best_len = site, length
    return best


def inspect_url(url):
    """Google se asli status. Returns InspectionResult(status, coverage_state).

    status: indexed / not_indexed (Google ne jawab diya) ya
            quota_exceeded / auth_error / permission_denied / error (jawab nahi mila).
    """
    try:
        site = find_property(url)
    except GoogleAccessError as exc:
        return InspectionResult(exc.status, '')
    if site is None:
        return InspectionResult('permission_denied', '')  # URL Google ko bheja hi nahi jata

    try:
        response = _get_session().post(
            INSPECT_URL,
            json={'inspectionUrl': url, 'siteUrl': site, 'languageCode': 'en-US'},
            timeout=TIMEOUT,
        )
        if response.status_code != 200:
            logger.warning('URL Inspection failed: HTTP %s', response.status_code)
            return InspectionResult(_status_for_http(response.status_code), '')
        index_status = response.json().get('inspectionResult', {}).get('indexStatusResult', {})
    except Exception as exc:
        logger.warning('URL Inspection error: %s', type(exc).__name__)
        return InspectionResult(_status_for_exception(exc), '')

    verdict = index_status.get('verdict')
    coverage = str(index_status.get('coverageState', ''))[:COVERAGE_MAX]
    if verdict == 'PASS':
        return InspectionResult('indexed', coverage)
    if verdict in ('NEUTRAL', 'FAIL'):
        return InspectionResult('not_indexed', coverage)
    return InspectionResult('error', '')


def request_indexing(url):
    """Indexing API (sirf JobPosting/livestream pages): 'submitted' / 'failed'.

    'submitted' ka matlab sirf itna ki Google ne request li, indexed hone ka saboot nahi.
    """
    try:
        response = _get_session().post(
            PUBLISH_URL, json={'url': url, 'type': 'URL_UPDATED'}, timeout=TIMEOUT)
        if response.status_code == 200:
            return 'submitted'
        logger.warning('Indexing API failed: HTTP %s', response.status_code)
    except Exception as exc:
        logger.warning('Indexing API error: %s', type(exc).__name__)
    return 'failed'