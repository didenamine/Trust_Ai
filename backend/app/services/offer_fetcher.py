"""Retrieve the text of a job offer from its URL (US08).

The API downloads pages on behalf of the user, so every URL (and every redirect hop) is
checked first: only http(s) on ports 80/443 towards public IP addresses is allowed. This
blocks attempts to reach localhost, the Docker network or cloud metadata endpoints (SSRF).

Text extraction, from most to least reliable:
1. the schema.org `JobPosting` JSON-LD block (LinkedIn, Welcome to the Jungle, most career
   sites publish it for Google Jobs): clean title, company, location and description;
2. otherwise the main content of the page, found by trafilatura, with the usual
   "similar jobs" / "alerts" sections cut off.
"""

import html
import ipaddress
import json
import re
import socket
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
import trafilatura

MAX_REDIRECTS = 5
MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024
MIN_CONTENT_CHARS = 50
MAX_CONTENT_CHARS = 50_000

_ALLOWED_PORTS = {None, 80, 443}
_TIMEOUT = httpx.Timeout(10.0)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TrustAIBot/0.1)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr,en;q=0.8",
}

_JSON_LD_RE = re.compile(
    r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)
# Sections that follow the real offer on most job boards (lowercase, straight apostrophes).
_TAIL_MARKERS = (
    "offres d'emploi similaires",
    "similar jobs",
    "autres pages consultées",
    "recevez des alertes",
    "les recommandations augmentent",
    "voir qui vous connaissez",
    "people also viewed",
    "show more jobs",
)
_MIN_CUT_INDEX = 200  # never cut so early that almost nothing is left
_APOSTROPHE = r"(?:'|’|&#0?39;|&#x27;|&rsquo;|&apos;)"
# A heading that opens a "similar jobs" style section: everything after it is not the offer.
_TAIL_HEADING_RE = re.compile(
    r"<h[1-6][^>]*>\s*(?:<[^>]+>\s*)*(?:"
    + "|".join(
        re.escape(marker).replace("'", _APOSTROPHE).replace(r"\ ", r"\s+")
        for marker in _TAIL_MARKERS
    )
    + ")",
    re.IGNORECASE,
)
_META_KEYWORDS_RES = (
    re.compile(
        r"""<meta\b[^>]*?\bname=["']keywords["'][^>]*?\bcontent=(["'])(.*?)\1""",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"""<meta\b[^>]*?\bcontent=(["'])(.*?)\1[^>]*?\bname=["']keywords["']""",
        re.IGNORECASE | re.DOTALL,
    ),
)
_SHOWS_KEYWORDS_RE = re.compile(r"mots[\s-]*cl(?:é|&eacute;|e)s", re.IGNORECASE)
# SEO filler that sites put first in <meta name="keywords"> ("offre d'emploi X, ...").
_SEO_PREFIXES = ("offre", "offres", "recrutement", "emploi", "job", "jobs", "recruitment")
_MAX_EXTRA_CHARS = 6000
# Visible lines that are page chrome, not offer facts (lowercase, straight apostrophes).
_NOISE_PREFIXES = (
    "postuler",
    "apply",
    "sauvegarder",
    "partagez",
    "découvrez qui",
    "n'attendez pas",
    "il'y a",
    "il y a",
)
# JobPosting fields worth keeping next to the description, as "label : value" lines.
_DETAIL_FIELDS = (
    ("Date de publication", "datePosted"),
    ("Date d'expiration", "validThrough"),
    ("Type de contrat", "employmentType"),
    ("Mode de travail", "jobLocationType"),
    ("Secteur", "industry"),
    ("Formation", "educationRequirements"),
    ("Expérience", "experienceRequirements"),
    ("Compétences", "skills"),
    ("Mots clés", "keywords"),
)
# Pages that answer 200 but only display "this job does not exist" (soft 404).
_ERROR_PHRASES = (
    "nous sommes désolés",
    "we're sorry",
    "we are sorry",
    "page not found",
    "page introuvable",
    "erreur 404",
    "error 404",
    "n'existe plus",
    "n'est plus disponible",
    "no longer available",
    "job not found",
    "a expiré",
    "has expired",
)


class UnsafeUrlError(Exception):
    """The URL targets a forbidden address (non-public IP, odd port, bad scheme)."""


class FetchFailedError(Exception):
    """The page could not be downloaded (DNS, timeout, HTTP error, too large...)."""


class NoContentError(Exception):
    """The page was downloaded but no usable offer text could be extracted."""


def _resolve_ips(hostname: str, port: int) -> list[str]:
    try:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FetchFailedError("Nom de domaine introuvable.") from exc
    return [str(info[4][0]) for info in infos]


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%")[0])
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global


def _assert_public_url(url: str) -> None:
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise UnsafeUrlError() from exc

    hostname = parts.hostname
    if parts.scheme not in ("http", "https") or not hostname or port not in _ALLOWED_PORTS:
        raise UnsafeUrlError()

    try:
        addresses = [str(ipaddress.ip_address(hostname))]
    except ValueError:
        addresses = _resolve_ips(hostname, port or (443 if parts.scheme == "https" else 80))

    if not all(_is_public(address) for address in addresses):
        raise UnsafeUrlError()


def _read_body(response: httpx.Response) -> bytes:
    if response.status_code >= 400:
        raise FetchFailedError(f"La page a répondu avec le code {response.status_code}.")

    content_type = response.headers.get("content-type", "").lower()
    if content_type and not content_type.startswith(("text/", "application/xhtml")):
        raise NoContentError("Ce lien ne pointe pas vers une page web.")

    body = bytearray()
    for chunk in response.iter_bytes():
        body.extend(chunk)
        if len(body) > MAX_DOWNLOAD_BYTES:
            raise FetchFailedError("La page est trop volumineuse.")
    return bytes(body)


def _download(url: str, transport: httpx.BaseTransport | None) -> bytes:
    current = url
    with httpx.Client(
        timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=False, transport=transport
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            _assert_public_url(current)
            try:
                with client.stream("GET", current) as response:
                    if response.is_redirect:
                        current = str(response.url.join(response.headers["location"]))
                    else:
                        return _read_body(response)
            except httpx.HTTPError as exc:
                raise FetchFailedError("Impossible de joindre cette adresse.") from exc
    raise FetchFailedError("Trop de redirections.")


def _clean(text: str) -> str:
    """Strip every line and collapse runs of blank lines and spaces."""
    lines = [re.sub(r"[ \t]{2,}", " ", line.strip()) for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _trim_boilerplate(text: str) -> str:
    """Cut the text where the "similar jobs" / "alerts" sections begin."""
    lowered = text.lower().replace("’", "'")
    cuts = [i for marker in _TAIL_MARKERS if (i := lowered.find(marker)) >= _MIN_CUT_INDEX]
    return text[: min(cuts)] if cuts else text


def _is_error_page(text: str) -> bool:
    head = text[:300].lower().replace("’", "'")
    return any(phrase in head for phrase in _ERROR_PHRASES)


def _as_text(value: object) -> str:
    return html.unescape(str(value)).strip() if value else ""


def _html_to_text(fragment: str) -> str:
    if "<" not in fragment and "&lt;" in fragment:  # HTML that was escaped twice
        fragment = html.unescape(fragment)
    fragment = re.sub(r"(?i)<br\s*/?>|</(?:p|div|h[1-6]|ul|ol|tr)>", "\n", fragment)
    fragment = re.sub(r"(?i)<li[^>]*>", "\n- ", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return _clean(html.unescape(fragment))


def _find_job_posting(data: object) -> dict | None:
    if isinstance(data, list):
        for item in data:
            if (found := _find_job_posting(item)) is not None:
                return found
    elif isinstance(data, dict):
        kind = data.get("@type")
        if kind == "JobPosting" or (isinstance(kind, list) and "JobPosting" in kind):
            return data
        return _find_job_posting(data.get("@graph"))
    return None


def _organization(posting: dict) -> str:
    org = posting.get("hiringOrganization")
    return _as_text(org.get("name") if isinstance(org, dict) else org)


def _location(posting: dict) -> str:
    place = posting.get("jobLocation")
    if isinstance(place, list):
        place = place[0] if place else None
    address = place.get("address") if isinstance(place, dict) else None
    if isinstance(address, str):
        return _as_text(address)
    if not isinstance(address, dict):
        return ""
    parts = [address.get("addressLocality"), address.get("addressRegion")]
    parts.append(address.get("addressCountry"))
    names = [part.get("name") if isinstance(part, dict) else part for part in parts]
    return ", ".join(_as_text(name) for name in names if name)


def _flatten(value: object) -> str:
    """Turn a JSON-LD value (text, list, or small object) into readable text."""
    if isinstance(value, list):
        return ", ".join(part for part in (_flatten(item) for item in value) if part)
    if isinstance(value, dict):
        if value.get("monthsOfExperience"):
            return f"{value['monthsOfExperience']} mois"
        return _as_text(value.get("name") or value.get("credentialCategory"))
    text = _as_text(value)
    return text[:10] if re.match(r"\d{4}-\d{2}-\d{2}T", text) else text  # drop the time


def _details(posting: dict) -> str:
    """Dates, contract type, skills, keywords... as "label : value" lines."""
    lines = []
    for label, key in _DETAIL_FIELDS:
        if value := _flatten(posting.get(key)):
            lines.append(f"{label} : {value}")
    return "\n".join(lines)


def _text_from_json_ld(page: str) -> str | None:
    """Title, company, location, details and description of a schema.org JobPosting."""
    for raw in _JSON_LD_RE.findall(page):
        try:
            data = json.loads(raw, strict=False)  # tolerate raw newlines
        except ValueError:
            continue
        posting = _find_job_posting(data)
        if posting is None:
            continue
        description = _html_to_text(str(posting.get("description") or ""))
        if len(description) < MIN_CONTENT_CHARS:
            continue
        meta = " · ".join(part for part in (_organization(posting), _location(posting)) if part)
        head = "\n".join(part for part in (_as_text(posting.get("title")), meta) if part)
        return "\n\n".join(part for part in (head, _details(posting), description) if part)
    return None


def _normalize(text: str) -> str:
    """Lowercase letters and digits only, to compare texts despite formatting differences."""
    return re.sub(r"\W+", "", text.lower())


def _extra_facts(visible: str, structured: str) -> str:
    """Lines of the visible page that the JSON-LD block does not already contain.

    JSON-LD is often incomplete: experience, study level, requirements... are frequently
    shown on the page only. They are appended after the structured text.
    """
    known = _normalize(structured)
    extras: list[str] = []
    for line in (raw.strip() for raw in visible.splitlines()):
        key = _normalize(line)
        text = line.lstrip("-•*· ").lower().replace("’", "'")
        if len(key) < 3 or key in known or "»" in line or text.startswith(_NOISE_PREFIXES):
            continue
        if extras and extras[-1].endswith(":"):  # "Experience :" then "Débutant"
            extras[-1] = f"{extras[-1]} {line.lstrip('-•*· ')}"
        else:
            extras.append(line)
        known += key  # a repeated line is only kept once
    return "\n".join(extras)[:_MAX_EXTRA_CHARS]


def _meta_keywords(page: str) -> str:
    """Keywords from <meta name="keywords">, only if the page itself shows a "Mots clés" section.

    Many job boards display the offer's keywords as links that text extraction drops, but
    repeat them in this meta tag (after a few SEO phrases, which are removed here).
    """
    if not _SHOWS_KEYWORDS_RE.search(page):
        return ""
    for pattern in _META_KEYWORDS_RES:
        if match := pattern.search(page):
            raw = re.sub(r"<!--.*?-->", "", html.unescape(match.group(2)), flags=re.DOTALL)
            break
    else:
        return ""
    keywords: list[str] = []
    for item in (part.strip() for part in raw.split(",")):
        if item and not item.lower().startswith(_SEO_PREFIXES) and item not in keywords:
            keywords.append(item)
    return ", ".join(keywords[:40])


def _visible_text(page: str) -> str:
    """Main text of the page, ignoring the "similar jobs" section and what follows it."""
    candidates = [page]
    if match := _TAIL_HEADING_RE.search(page):
        candidates.insert(0, page[: match.start()])  # if this cut removes the offer, retry
    for candidate in candidates:
        extracted = trafilatura.extract(candidate, include_comments=False, favor_recall=True)
        text = _trim_boilerplate(_clean(extracted or ""))
        if len(text) >= MIN_CONTENT_CHARS:
            return text
    return ""


def fetch_offer_text(url: str, *, transport: httpx.BaseTransport | None = None) -> str:
    """Download `url` and return the text of the job offer (without page boilerplate)."""
    page = _download(url, transport).decode("utf-8", errors="replace")

    visible = _visible_text(page)
    structured = _text_from_json_ld(page)
    if structured is None:
        text = visible
    else:
        text = "\n\n".join(part for part in (structured, _extra_facts(visible, structured)) if part)

    keywords = _meta_keywords(page)
    if keywords and "mots clés" not in text.lower():
        text = f"{text}\n\nMots clés : {keywords}"

    if len(text) < MIN_CONTENT_CHARS or _is_error_page(text):
        raise NoContentError("Aucun texte d'offre n'a pu être extrait de cette page.")
    return text[:MAX_CONTENT_CHARS]


_TRACKING_PARAMS = {"fbclid", "gclid", "refid", "trackingid", "trk"}


def normalize_url(url: str) -> str:
    """Canonical form of a URL, so cosmetic variants of one offer are saved only once."""
    parts = urlsplit(url.strip())
    query = sorted(
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in _TRACKING_PARAMS
    )
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))
