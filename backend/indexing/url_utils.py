import hashlib
from urllib.parse import urlsplit, urlunsplit


def normalize_url(raw_url):
    """URL ko ek standard shakal deta hai taaki duplicate sahi pakda jaye.

    - aage/peeche ki whitespace hatao
    - scheme aur host ko lowercase karo (HTTPS://EXAMPLE.com == https://example.com)
    - #fragment hatao (browser-only hissa hai, server tak nahi jata)
    - path aur query jaisi hain waisi rakho (path case-sensitive hota hai)
    - trailing slash khud se add/remove nahi karte
    """
    parts = urlsplit(raw_url.strip())
    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        parts.path,
        parts.query,
        '',
    ))


def hash_url(url):
    """Normalized URL ka SHA-256 (64 hex characters). Empty path ko '/' maana jata hai.

    Lambe URL column par unique index MySQL mein nahi ban sakta, isliye
    uniqueness is chhote hash par lagti hai.
    """
    parts = urlsplit(normalize_url(url))
    # https://example.com aur https://example.com/ HTTP mein same page hain
    canonical = urlunsplit((parts.scheme, parts.netloc, parts.path or '/',
                            parts.query, ''))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()