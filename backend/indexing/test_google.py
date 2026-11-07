"""Google integration tests. Google ko hamesha mock kiya jata hai (asli call kabhi nahi)."""
from unittest import mock

import requests
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from google.auth.exceptions import DefaultCredentialsError
from rest_framework import status

from . import google_client, services
from .google_client import GoogleAccessError, InspectionResult
from .models import URLSubmission
from .testing import CleanAPITestCase

GOOGLE_ON = dict(GOOGLE_ENABLED=True, GOOGLE_SERVICE_ACCOUNT_FILE='',
                 GOOGLE_CLOUD_PROJECT='', GOOGLE_INDEXING_API_ENABLED=False)
GOOGLE_ON_WITH_INDEXING = {**GOOGLE_ON, 'GOOGLE_INDEXING_API_ENABLED': True}

OWNED = [{'siteUrl': 'sc-domain:example.com', 'permissionLevel': 'siteOwner'}]


def fake_response(status_code=200, body=None):
    response = mock.Mock()
    response.status_code = status_code
    response.json.return_value = body if body is not None else {}
    return response


def inspection_body(verdict, coverage='Some coverage text'):
    return {'inspectionResult': {'indexStatusResult': {
        'verdict': verdict, 'coverageState': coverage}}}


def sites_response(entries=OWNED):
    return fake_response(200, {'siteEntry': entries})


class GoogleTestMixin:
    """Har test se pehle properties ka cache saaf, taaki tests ek dusre ko na chhuyein."""

    def setUp(self):
        super().setUp()
        google_client.clear_cache()
        self.addCleanup(google_client.clear_cache)


# ---------------------------------------------------------------- unit: google_client

@override_settings(**GOOGLE_ON)
class ConfigTests(GoogleTestMixin, SimpleTestCase):
    def test_is_configured_follows_google_enabled(self):
        self.assertTrue(google_client.is_configured())
        with override_settings(GOOGLE_ENABLED=False):
            self.assertFalse(google_client.is_configured())


@override_settings(**GOOGLE_ON)
class ListPropertiesTests(GoogleTestMixin, SimpleTestCase):
    def run_list(self, response=None, error=None):
        with mock.patch.object(google_client, '_get_session') as get_session:
            if error:
                get_session.side_effect = error
            else:
                get_session.return_value.get.return_value = response
            return google_client.list_properties(), get_session

    def test_returns_site_entries(self):
        result, _ = self.run_list(sites_response())
        self.assertEqual(result, OWNED)

    def test_result_is_cached(self):
        with mock.patch.object(google_client, '_get_session') as get_session:
            get_session.return_value.get.return_value = sites_response()
            google_client.list_properties()
            google_client.list_properties()
        self.assertEqual(get_session.return_value.get.call_count, 1)

    def test_http_errors_map_to_clear_statuses(self):
        expected = {401: 'auth_error', 403: 'permission_denied',
                    429: 'quota_exceeded', 500: 'error'}
        for code, name in expected.items():
            google_client.clear_cache()
            with mock.patch.object(google_client, '_get_session') as get_session:
                get_session.return_value.get.return_value = fake_response(code)
                with self.assertRaises(GoogleAccessError) as ctx:
                    google_client.list_properties()
            self.assertEqual(ctx.exception.status, name, code)

    def test_missing_credentials_is_auth_error(self):
        with self.assertRaises(GoogleAccessError) as ctx:
            self.run_list(error=DefaultCredentialsError('no creds'))
        self.assertEqual(ctx.exception.status, 'auth_error')

    def test_timeout_is_error_not_auth_error(self):
        with mock.patch.object(google_client, '_get_session') as get_session:
            get_session.return_value.get.side_effect = requests.exceptions.Timeout('slow')
            with self.assertRaises(GoogleAccessError) as ctx:
                google_client.list_properties()
        self.assertEqual(ctx.exception.status, 'error')

    def test_failure_is_not_cached(self):
        with mock.patch.object(google_client, '_get_session') as get_session:
            get_session.return_value.get.return_value = fake_response(500)
            with self.assertRaises(GoogleAccessError):
                google_client.list_properties()
            get_session.return_value.get.return_value = sites_response()
            self.assertEqual(google_client.list_properties(), OWNED)

    def test_exception_text_is_not_logged(self):
        with self.assertLogs('indexing.google_client', 'WARNING') as logs:
            with self.assertRaises(GoogleAccessError):
                self.run_list(error=RuntimeError('secret-token-123'))
        self.assertNotIn('secret-token-123', ' '.join(logs.output))


@override_settings(**GOOGLE_ON)
class FindPropertyTests(GoogleTestMixin, SimpleTestCase):
    def find(self, url, entries):
        with mock.patch.object(google_client, 'list_properties', return_value=entries):
            return google_client.find_property(url)

    def test_domain_property_matches_domain_and_subdomains(self):
        self.assertEqual(self.find('https://example.com/a', OWNED), 'sc-domain:example.com')
        self.assertEqual(self.find('https://www.example.com/a', OWNED), 'sc-domain:example.com')

    def test_lookalike_and_third_party_hosts_do_not_match(self):
        for url in ('https://evil-example.com/', 'https://example.com.evil.com/',
                    'https://prezi.com/x', 'https://archive.org/y'):
            self.assertIsNone(self.find(url, OWNED), url)

    def test_url_prefix_property_matches_only_its_prefix(self):
        entries = [{'siteUrl': 'https://example.com/blog/', 'permissionLevel': 'siteOwner'}]
        self.assertEqual(self.find('https://example.com/blog/p', entries),
                         'https://example.com/blog/')
        self.assertIsNone(self.find('https://example.com/shop/', entries))

    def test_unverified_property_is_never_used(self):
        entries = [{'siteUrl': 'sc-domain:example.com',
                    'permissionLevel': 'siteUnverifiedUser'}]
        self.assertIsNone(self.find('https://example.com/a', entries))

    def test_most_specific_property_wins(self):
        entries = [
            {'siteUrl': 'sc-domain:example.com', 'permissionLevel': 'siteOwner'},
            {'siteUrl': 'https://example.com/blog/', 'permissionLevel': 'siteFullUser'},
        ]
        self.assertEqual(self.find('https://example.com/blog/p', entries),
                         'https://example.com/blog/')


@override_settings(**GOOGLE_ON)
class InspectUrlTests(GoogleTestMixin, SimpleTestCase):
    URL = 'https://example.com/a'

    def run_inspect(self, response=None, error=None, property_='sc-domain:example.com'):
        with mock.patch.object(google_client, 'find_property', return_value=property_), \
                mock.patch.object(google_client, '_get_session') as get_session:
            post = get_session.return_value.post
            if error:
                post.side_effect = error
            else:
                post.return_value = response
            return google_client.inspect_url(self.URL), post

    def test_pass_means_indexed_and_keeps_googles_coverage_text(self):
        result, _ = self.run_inspect(fake_response(200, inspection_body('PASS', 'Submitted and indexed')))
        self.assertEqual(result, InspectionResult('indexed', 'Submitted and indexed'))

    def test_unknown_to_google_is_not_indexed_with_googles_words(self):
        result, _ = self.run_inspect(
            fake_response(200, inspection_body('NEUTRAL', 'URL is unknown to Google')))
        self.assertEqual(result.status, 'not_indexed')
        self.assertEqual(result.coverage_state, 'URL is unknown to Google')

    def test_fail_is_not_indexed(self):
        result, _ = self.run_inspect(fake_response(200, inspection_body('FAIL')))
        self.assertEqual(result.status, 'not_indexed')

    def test_unknown_or_missing_verdict_is_error_never_fake_success(self):
        for body in (inspection_body('VERDICT_UNSPECIFIED'), {}):
            result, _ = self.run_inspect(fake_response(200, body))
            self.assertEqual(result.status, 'error')
            self.assertEqual(result.coverage_state, '')

    def test_http_failures_are_separate_statuses_not_not_indexed(self):
        expected = {401: 'auth_error', 403: 'permission_denied',
                    429: 'quota_exceeded', 400: 'error', 500: 'error'}
        for code, name in expected.items():
            result, _ = self.run_inspect(fake_response(code))
            self.assertEqual(result, InspectionResult(name, ''), code)

    def test_timeout_is_error(self):
        result, _ = self.run_inspect(error=requests.exceptions.Timeout('slow'))
        self.assertEqual(result.status, 'error')

    def test_credential_failure_is_auth_error(self):
        result, _ = self.run_inspect(error=DefaultCredentialsError('x'))
        self.assertEqual(result.status, 'auth_error')

    def test_url_without_a_property_is_permission_denied_and_never_sent(self):
        result, post = self.run_inspect(fake_response(200), property_=None)
        self.assertEqual(result.status, 'permission_denied')
        post.assert_not_called()

    def test_property_listing_failure_is_reported_not_hidden(self):
        with mock.patch.object(google_client, 'find_property',
                               side_effect=GoogleAccessError('quota_exceeded')):
            self.assertEqual(google_client.inspect_url(self.URL).status, 'quota_exceeded')

    def test_sends_url_and_matched_property_to_google(self):
        _, post = self.run_inspect(fake_response(200, inspection_body('PASS')))
        args, kwargs = post.call_args
        self.assertEqual(args[0], google_client.INSPECT_URL)
        self.assertEqual(kwargs['json'], {
            'inspectionUrl': self.URL, 'siteUrl': 'sc-domain:example.com',
            'languageCode': 'en-US'})
        self.assertIn('timeout', kwargs)

    def test_very_long_coverage_text_is_cut_to_fit_database(self):
        result, _ = self.run_inspect(fake_response(200, inspection_body('PASS', 'x' * 1000)))
        self.assertLessEqual(len(result.coverage_state), 255)

    def test_no_secret_in_logs(self):
        with self.assertLogs('indexing.google_client', 'WARNING') as logs:
            self.run_inspect(error=RuntimeError('secret-token-123'))
        self.assertNotIn('secret-token-123', ' '.join(logs.output))


@override_settings(**GOOGLE_ON_WITH_INDEXING)
class RequestIndexingTests(GoogleTestMixin, SimpleTestCase):
    def run_request(self, response=None, error=None):
        with mock.patch.object(google_client, '_get_session') as get_session:
            if error:
                get_session.return_value.post.side_effect = error
            else:
                get_session.return_value.post.return_value = response
            return google_client.request_indexing('https://example.com/job/1'), \
                get_session.return_value.post

    def test_http_200_means_submitted(self):
        result, post = self.run_request(fake_response(200))
        self.assertEqual(result, 'submitted')
        args, kwargs = post.call_args
        self.assertEqual(args[0], google_client.PUBLISH_URL)
        self.assertEqual(kwargs['json'], {'url': 'https://example.com/job/1',
                                          'type': 'URL_UPDATED'})

    def test_http_errors_and_exceptions_mean_failed(self):
        for code in (400, 403, 429, 500):
            self.assertEqual(self.run_request(fake_response(code))[0], 'failed')
        self.assertEqual(self.run_request(error=RuntimeError('boom'))[0], 'failed')


# ---------------------------------------------------------------- unit: services

@override_settings(**GOOGLE_ON)
class ServicesTests(GoogleTestMixin, CleanAPITestCase):
    def make(self):
        return URLSubmission.objects.create(url='https://example.com/a')

    def run_process(self, result, fn=services.process_submission, record=None):
        record = record or self.make()
        with mock.patch.object(services.google_client, 'inspect_url', return_value=result):
            fn(record)
        record.refresh_from_db()
        return record

    @override_settings(GOOGLE_ENABLED=False)
    def test_does_nothing_when_google_disabled(self):
        record = self.make()
        with mock.patch.object(services.google_client, 'inspect_url') as inspect:
            services.process_submission(record)
        inspect.assert_not_called()
        record.refresh_from_db()
        self.assertEqual(record.inspection_status, 'not_inspected')

    def test_saves_status_coverage_and_timestamp_for_real_answer(self):
        record = self.run_process(InspectionResult('not_indexed', 'URL is unknown to Google'))
        self.assertEqual(record.inspection_status, 'not_indexed')
        self.assertEqual(record.coverage_state, 'URL is unknown to Google')
        self.assertIsNotNone(record.last_inspected_at)

    def test_error_states_set_no_inspection_timestamp(self):
        for name in ('quota_exceeded', 'auth_error', 'permission_denied', 'error'):
            URLSubmission.objects.all().delete()
            record = self.run_process(InspectionResult(name, ''))
            self.assertEqual(record.inspection_status, name)
            self.assertIsNone(record.last_inspected_at)

    def test_indexing_api_not_called_when_disabled(self):
        with mock.patch.object(services.google_client, 'request_indexing') as request:
            self.run_process(InspectionResult('not_indexed', ''))
        request.assert_not_called()

    @override_settings(**GOOGLE_ON_WITH_INDEXING)
    def test_indexing_api_only_when_enabled_and_confirmed_not_indexed(self):
        with mock.patch.object(services.google_client, 'request_indexing',
                               return_value='submitted') as request:
            record = self.run_process(InspectionResult('not_indexed', ''))
            self.assertEqual(record.indexing_request_status, 'submitted')
            request.assert_called_once_with('https://example.com/a')

            request.reset_mock()
            for name in ('indexed', 'quota_exceeded', 'auth_error', 'permission_denied', 'error'):
                URLSubmission.objects.all().delete()
                self.run_process(InspectionResult(name, ''))
            request.assert_not_called()  # kabhi nahi: na indexed par, na error par

    @override_settings(**GOOGLE_ON_WITH_INDEXING)
    def test_refresh_status_never_sends_indexing_request(self):
        with mock.patch.object(services.google_client, 'request_indexing') as request:
            self.run_process(InspectionResult('not_indexed', ''), fn=services.refresh_status)
        request.assert_not_called()


# ---------------------------------------------------------------- integration: API

@override_settings(**GOOGLE_ON)
class SubmitWithGoogleTests(GoogleTestMixin, CleanAPITestCase):
    def submit(self, url):
        return self.client.post(reverse('url-list'), {'url': url}, format='json')

    def patch_google(self, result=InspectionResult('indexed', 'Submitted and indexed'),
                     property_='sc-domain:example.com'):
        return (mock.patch.object(services.google_client, 'find_property', return_value=property_),
                mock.patch.object(services.google_client, 'inspect_url', return_value=result))

    def test_url_outside_authorized_properties_is_400_and_never_inspected(self):
        find, inspect = self.patch_google(property_=None)
        with find, inspect as inspect_mock:
            response = self.submit('https://prezi.com/some-deck')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(URLSubmission.objects.count(), 0)
        inspect_mock.assert_not_called()

    def test_invalid_url_never_reaches_google(self):
        find, inspect = self.patch_google()
        with find as find_mock, inspect as inspect_mock:
            response = self.submit('not-a-valid-url')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        find_mock.assert_not_called()
        inspect_mock.assert_not_called()

    def test_valid_url_shows_real_google_answer(self):
        find, inspect = self.patch_google(InspectionResult('not_indexed', 'URL is unknown to Google'))
        with find, inspect:
            response = self.submit('https://example.com/page')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['inspection_status'], 'not_indexed')
        self.assertEqual(response.data['coverage_state'], 'URL is unknown to Google')
        self.assertIsNotNone(response.data['last_inspected_at'])

    def test_quota_exceeded_is_shown_as_quota_not_as_indexing_success(self):
        find, inspect = self.patch_google(InspectionResult('quota_exceeded', ''))
        with find, inspect:
            response = self.submit('https://example.com/page')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['inspection_status'], 'quota_exceeded')
        self.assertEqual(response.data['indexing_request_status'], 'not_requested')

    def test_google_unavailable_while_checking_property_is_503_and_saves_nothing(self):
        for name in ('auth_error', 'quota_exceeded', 'error'):
            with mock.patch.object(services.google_client, 'find_property',
                                   side_effect=GoogleAccessError(name)):
                response = self.submit('https://example.com/page')
            self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            self.assertEqual(URLSubmission.objects.count(), 0)
            self.assertNotIn(name, str(response.data))  # andar ki details bahar nahi

    def test_duplicate_submit_inspects_again_and_keeps_one_record(self):
        find, _ = self.patch_google()
        with find, mock.patch.object(
                services.google_client, 'inspect_url',
                side_effect=[InspectionResult('not_indexed', ''),
                             InspectionResult('indexed', 'Submitted and indexed')]) as inspect:
            first = self.submit('https://example.com/page')
            second = self.submit('https://example.com/page')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data['inspection_status'], 'indexed')
        self.assertEqual(inspect.call_count, 2)
        self.assertEqual(URLSubmission.objects.count(), 1)

    def test_response_has_only_safe_fields(self):
        find, inspect = self.patch_google()
        with find, inspect:
            response = self.submit('https://example.com/page')
        self.assertEqual(set(response.data), {
            'id', 'url', 'inspection_status', 'indexing_request_status',
            'coverage_state', 'last_inspected_at', 'created_at', 'updated_at'})

    def test_client_cannot_set_status_fields(self):
        find, inspect = self.patch_google(InspectionResult('not_indexed', ''))
        with find, inspect:
            response = self.client.post(reverse('url-list'), {
                'url': 'https://example.com/page', 'inspection_status': 'indexed',
                'coverage_state': 'fake', 'last_inspected_at': '2020-01-01T00:00:00Z',
            }, format='json')
        self.assertEqual(response.data['inspection_status'], 'not_indexed')
        self.assertNotEqual(response.data['coverage_state'], 'fake')


@override_settings(**GOOGLE_ON)
class RecheckEndpointTests(GoogleTestMixin, CleanAPITestCase):
    def make(self):
        return URLSubmission.objects.create(
            url='https://example.com/a', inspection_status='not_indexed')

    def recheck(self, pk):
        return self.client.post(reverse('url-recheck', args=[pk]))

    def test_recheck_updates_status_from_google(self):
        record = self.make()
        with mock.patch.object(services.google_client, 'inspect_url',
                               return_value=InspectionResult('indexed', 'Submitted and indexed')):
            response = self.recheck(record.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['inspection_status'], 'indexed')
        record.refresh_from_db()
        self.assertEqual(record.coverage_state, 'Submitted and indexed')

    def test_recheck_does_not_move_url_in_list(self):
        record = self.make()
        before = record.updated_at
        with mock.patch.object(services.google_client, 'inspect_url',
                               return_value=InspectionResult('indexed', '')):
            self.recheck(record.pk)
        record.refresh_from_db()
        self.assertEqual(record.updated_at, before)

    @override_settings(GOOGLE_INDEXING_API_ENABLED=True)
    def test_recheck_never_sends_indexing_request(self):
        record = self.make()
        with mock.patch.object(services.google_client, 'inspect_url',
                               return_value=InspectionResult('not_indexed', '')), \
                mock.patch.object(services.google_client, 'request_indexing') as request:
            self.recheck(record.pk)
        request.assert_not_called()

    def test_unknown_id_is_404(self):
        self.assertEqual(self.recheck(99999).status_code, status.HTTP_404_NOT_FOUND)

    def test_get_is_not_allowed(self):
        response = self.client.get(reverse('url-recheck', args=[self.make().pk]))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @override_settings(GOOGLE_ENABLED=False)
    def test_returns_503_when_google_disabled(self):
        self.assertEqual(self.recheck(self.make().pk).status_code,
                         status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_recheck_is_rate_limited(self):
        record = self.make()
        with mock.patch.object(services.google_client, 'inspect_url',
                               return_value=InspectionResult('indexed', '')):
            codes = [self.recheck(record.pk).status_code for _ in range(12)]
        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, codes)
        
# ---------------------------------------------------------------- test isolation + architecture

class TestIsolationTests(SimpleTestCase):
    """Tests kabhi aapki asli .env ke Google settings par nahi chalne chahiye."""

    def test_google_is_forced_off_while_running_tests(self):
        from django.conf import settings
        self.assertTrue(settings.TESTING)
        self.assertFalse(settings.GOOGLE_ENABLED)
        self.assertFalse(settings.GOOGLE_INDEXING_API_ENABLED)
        self.assertEqual(settings.GOOGLE_SERVICE_ACCOUNT_FILE, '')


@override_settings(**GOOGLE_ON)
class SerializerIsFormatOnlyTests(GoogleTestMixin, SimpleTestCase):
    """Serializer sirf URL ki shakal check karta hai; Google se kuch nahi poochhta."""

    def test_valid_url_needs_no_google_even_when_google_is_enabled(self):
        from .serializers import URLSubmissionSerializer
        with mock.patch.object(google_client, 'find_property') as find, \
                mock.patch.object(google_client, '_get_session') as session:
            s = URLSubmissionSerializer(data={'url': 'https://anything-at-all.test/page'})
            self.assertTrue(s.is_valid(), s.errors)
        find.assert_not_called()
        session.assert_not_called()

    def test_bad_format_is_still_rejected(self):
        from .serializers import URLSubmissionSerializer
        for bad in ('not-a-url', 'ftp://example.com', 'https://user:pw@example.com'):
            self.assertFalse(URLSubmissionSerializer(data={'url': bad}).is_valid(), bad)


@override_settings(**GOOGLE_ON)
class EnsureAuthorizedTests(GoogleTestMixin, SimpleTestCase):

    def test_authorized_url_passes(self):
        with mock.patch.object(services.google_client, 'find_property',
                               return_value='sc-domain:example.com'):
            services.ensure_authorized('https://example.com/a')  # no exception

    def test_unauthorized_url_raises(self):
        with mock.patch.object(services.google_client, 'find_property', return_value=None):
            with self.assertRaises(services.URLNotAuthorized):
                services.ensure_authorized('https://example.com/a')

    def test_google_failure_is_not_mistaken_for_unauthorized(self):
        with mock.patch.object(services.google_client, 'find_property',
                               side_effect=GoogleAccessError('quota_exceeded')):
            with self.assertRaises(GoogleAccessError):
                services.ensure_authorized('https://example.com/a')

    @override_settings(GOOGLE_ENABLED=False)
    def test_does_nothing_when_google_disabled(self):
        with mock.patch.object(services.google_client, 'find_property') as find:
            services.ensure_authorized('https://example.com/a')
        find.assert_not_called()


TRIP_CANVAS = [{'siteUrl': 'https://trip-canvas-livid.vercel.app/',
                'permissionLevel': 'siteOwner'}]


@override_settings(**GOOGLE_ON)
class TripCanvasPropertyTests(GoogleTestMixin, CleanAPITestCase):
    """Asli matching code chalta hai; sirf Google ka network/login mock hai."""

    def submit(self, url):
        return self.client.post(reverse('url-list'), {'url': url}, format='json')

    def run_submit(self, url):
        with mock.patch.object(google_client, 'list_properties', return_value=TRIP_CANVAS), \
                mock.patch.object(google_client, '_get_session') as session:
            session.return_value.post.return_value = fake_response(
                200, inspection_body('NEUTRAL', 'URL is unknown to Google'))
            response = self.submit(url)
        return response, session.return_value.post

    def test_homepage_of_owned_property_is_inspected_with_that_property(self):
        response, post = self.run_submit('https://trip-canvas-livid.vercel.app/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['inspection_status'], 'not_indexed')
        self.assertEqual(post.call_args.kwargs['json']['siteUrl'],
                         'https://trip-canvas-livid.vercel.app/')

    def test_page_inside_owned_property_is_allowed(self):
        response, post = self.run_submit('https://trip-canvas-livid.vercel.app/about')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post.assert_called_once()

    def test_unowned_example_com_is_400_saved_nowhere_and_never_sent_to_google(self):
        response, post = self.run_submit('https://example.com/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(URLSubmission.objects.count(), 0)
        post.assert_not_called()

    def test_urls_outside_the_property_are_rejected_before_google_is_called(self):
        outside = [
            'https://trip-canvas-livid.vercel.app.evil.com/',  # lookalike host
            'https://other-app.vercel.app/',                   # same platform, other site
            'http://trip-canvas-livid.vercel.app/',            # property https hai, ye http
            'https://prezi.com/some-deck',
            'https://archive.org/details/x',
        ]
        for url in outside:
            response, post = self.run_submit(url)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, url)
            post.assert_not_called()
        self.assertEqual(URLSubmission.objects.count(), 0)