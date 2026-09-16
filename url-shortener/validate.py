"""URL validation and short-code rules.

A URL shortener is a small program with a large attack surface, because its
whole job is to take a string from a stranger and later send somebody else to
it. Three things are checked here, and each corresponds to a real way
shorteners get abused:

1. Scheme. `javascript:alert(1)` and `data:text/html,...` are perfectly valid
   URLs. Storing one and emitting it in a Location header or an href turns the
   service into an XSS delivery mechanism. Only http and https survive.

2. Reserved aliases. The app serves its own routes off the root, so a custom
   alias of "api" or "static" would shadow them and quietly break the service
   for everyone.

3. Self-reference. Shortening the shortener's own short link creates a
   redirect loop that costs a request per hop forever.
"""

from urllib.parse import urlsplit, urlunsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})

# every path segment the app itself answers on
RESERVED = frozenset({
    "api", "static", "stats", "s", "admin", "login", "health",
    "favicon.ico", "robots.txt", "index", "new", "about",
})

ALIAS_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
MAX_URL_LEN = 2048
ALIAS_MIN, ALIAS_MAX = 3, 32


class ValidationError(ValueError):
    """Raised with a message meant to be shown to the user."""


def normalize_url(raw):
    """Trim, add a default scheme, and lower-case the host.

    The scheme check runs on the RESULT, so adding a default can never be a way
    to smuggle one past the allowlist.
    """
    if raw is None:
        raise ValidationError("Enter a URL.")
    url = str(raw).strip()
    if not url:
        raise ValidationError("Enter a URL.")
    if len(url) > MAX_URL_LEN:
        raise ValidationError(f"That URL is longer than {MAX_URL_LEN} characters.")

    # control characters are used to smuggle "java\tscript:" past naive checks
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in url):
        raise ValidationError("That URL contains control characters.")

    # a bare "example.com/x" has no scheme; urlsplit would read "example.com" as one
    if "://" not in url:
        head = url.split("/", 1)[0]
        if ":" in head and not head.split(":", 1)[1].isdigit():
            raise ValidationError("Only http and https links can be shortened.")
        url = "http://" + url

    parts = urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValidationError("Only http and https links can be shortened.")
    if not parts.hostname:
        raise ValidationError("That URL has no host.")
    if "." not in parts.hostname and parts.hostname != "localhost":
        raise ValidationError("That host does not look like a real domain.")

    host = parts.hostname.lower()
    netloc = f"{host}:{parts.port}" if parts.port else host
    if parts.username:
        # user:pass@host is how a link is disguised as pointing somewhere else
        raise ValidationError("Credentials in a URL are not allowed.")
    return urlunsplit((parts.scheme.lower(), netloc, parts.path, parts.query, parts.fragment))


def check_not_self(url, own_hosts):
    """Reject shortening a link that points back at this service."""
    host = (urlsplit(url).hostname or "").lower()
    if host in {h.lower() for h in own_hosts}:
        raise ValidationError("That link already points at this shortener.")
    return url


def validate_alias(alias):
    """Validate a user-chosen short code, or return None if none was given."""
    if alias is None or str(alias).strip() == "":
        return None
    a = str(alias).strip()
    if not (ALIAS_MIN <= len(a) <= ALIAS_MAX):
        raise ValidationError(f"A custom alias must be {ALIAS_MIN}-{ALIAS_MAX} characters.")
    if not set(a) <= ALIAS_CHARS:
        raise ValidationError("A custom alias can use letters, digits, hyphen and underscore only.")
    if a.lower() in RESERVED:
        raise ValidationError(f"'{a}' is reserved by this site.")
    return a
