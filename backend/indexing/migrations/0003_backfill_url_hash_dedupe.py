import hashlib
from urllib.parse import urlsplit, urlunsplit

from django.db import migrations


# NOTE: helper functions yahan copy kiye hain (app code import nahi kiya), taaki
# future mein url_utils badle to is purani migration ka behaviour na badle.
def _normalize(raw_url):
    parts = urlsplit(raw_url.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                       parts.path, parts.query, ''))


def _hash(url):
    parts = urlsplit(_normalize(url))
    canonical = urlunsplit((parts.scheme, parts.netloc, parts.path or '/',
                            parts.query, ''))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def backfill_url_hash_and_merge_duplicates(apps, schema_editor):
    """Purane rows ka url normalize karo, hash bharo, duplicates hatao.

    Duplicate mile to sabse purana record (sabse chhota id) rakhte hain, baaki
    delete hote hain. Ye delete wapas nahi laaya ja sakta (reverse = no-op).
    """
    URLSubmission = apps.get_model('indexing', 'URLSubmission')
    seen = set()
    for pk, url in list(URLSubmission.objects.order_by('pk').values_list('pk', 'url')):
        normalized = _normalize(url)
        url_hash = _hash(url)
        if url_hash in seen:
            URLSubmission.objects.filter(pk=pk).delete()
            continue
        seen.add(url_hash)
        URLSubmission.objects.filter(pk=pk).update(url=normalized, url_hash=url_hash)


class Migration(migrations.Migration):
    """Step 2/3: data migration."""

    dependencies = [
        ('indexing', '0002_add_status_fields_and_url_hash'),
    ]

    operations = [
        migrations.RunPython(
            backfill_url_hash_and_merge_duplicates,
            migrations.RunPython.noop,
        ),
    ]