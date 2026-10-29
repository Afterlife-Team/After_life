"""Bounded best-effort reconstruction from the Wayback Machine.

Only calls fixed Internet Archive hosts, never user-controlled origins. Historical
sites are often incomplete; missing assets/pages are reported, not invented.
"""
from collections import deque
from contextlib import closing
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import math
import sqlite3
import time
import hashlib
import posixpath
import re
from urllib.parse import urljoin, urlsplit, urldefrag
import requests
from bs4 import BeautifulSoup
from services.security import validate_public_url
from services.site_bundle import SiteBundle

WAYBACK = 'https://web.archive.org'
AVAILABILITY = 'https://archive.org/wayback/available'
CDX = 'https://web.archive.org/cdx/search/cdx'
HEADERS = {'User-Agent':'404Afterlife/2.0 (educational website recovery)'}
MAX_PAGES = 12
MAX_ASSETS = 60
MAX_BYTES = 20 * 1024 * 1024
MAX_RESOURCE = 3 * 1024 * 1024
IMG_EXT = {'.png','.jpg','.jpeg','.gif','.svg','.ico','.webp','.bmp'}
CSS_EXT = {'.css'}
FONTS = {'.woff','.woff2','.ttf','.otf'}
HTML_LIKE = {'','.html','.htm','.php','.asp','.aspx','.jsp'}

class ArchiveError(RuntimeError):
    """A Wayback lookup or archive recovery failed."""


class ArchiveRateLimited(ArchiveError):
    """The archive returned HTTP 429; do not immediately try another endpoint."""


# All cache data comes from the allowlisted Internet Archive hosts. The cache
# is local to this project and persists across Streamlit reruns/restarts.
# Delete .cache/wayback.sqlite3 to clear it. Do not commit .cache/ to Git.
CACHE_DB = Path(__file__).resolve().parent.parent / '.cache' / 'wayback.sqlite3'
CACHE_MAX_BYTES = 64 * 1024 * 1024
CACHE_AVAILABILITY_SECONDS = 60 * 60
CACHE_ARCHIVED_SECONDS = 7 * 24 * 60 * 60
DEFAULT_RATE_LIMIT_SECONDS = 5 * 60
MAX_RETRY_AFTER_SECONDS = 7 * 24 * 60 * 60
_in_memory_cooldown = 0.0


def _db():
    """Open a bounded local response cache; fail open if its folder is unwritable."""
    try:
        CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(CACHE_DB, timeout=2)
        db.execute("""CREATE TABLE IF NOT EXISTS responses (
            request_key TEXT PRIMARY KEY,
            body BLOB NOT NULL,
            content_type TEXT NOT NULL,
            expires_at REAL NOT NULL,
            created_at REAL NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS state (
            name TEXT PRIMARY KEY, value REAL NOT NULL
        )""")
        db.commit()
        return db
    except (OSError, sqlite3.Error):
        return None


def _request_key(url, params):
    # Cache by the complete request, including requested original URL/year.
    try:
        prepared = requests.Request('GET', url, params=params).prepare()
        return hashlib.sha256(prepared.url.encode('utf-8')).hexdigest()
    except (ValueError, TypeError, requests.RequestException) as exc:
        raise ArchiveError('Invalid Wayback request parameters.') from exc


def _cached_response(key):
    db = _db()
    if db is None:
        return None
    with closing(db):
        try:
            row = db.execute(
                'SELECT body, content_type FROM responses WHERE request_key=? AND expires_at>?',
                (key, time.time())
            ).fetchone()
            return (row[0], row[1]) if row else None
        except sqlite3.Error:
            return None


def _cache_success(key, body, content_type, url):
    # A large result should not cause unbounded cache growth.
    if len(body) > MAX_RESOURCE:
        return
    duration = (CACHE_AVAILABILITY_SECONDS if urlsplit(url).path.startswith(('/wayback/available','/cdx/'))
                else CACHE_ARCHIVED_SECONDS)
    db = _db()
    if db is None:
        return
    with closing(db):
        try:
            now = time.time()
            with db:
                db.execute('DELETE FROM responses WHERE expires_at <= ?', (now,))
                db.execute("""INSERT OR REPLACE INTO responses
                    (request_key, body, content_type, expires_at, created_at)
                    VALUES (?,?,?,?,?)""", (key, body, content_type, now + duration, now))
                total = db.execute('SELECT COALESCE(SUM(LENGTH(body)),0) FROM responses').fetchone()[0]
                while total > CACHE_MAX_BYTES:
                    oldest = db.execute('SELECT request_key,LENGTH(body) FROM responses ORDER BY created_at LIMIT 1').fetchone()
                    if not oldest:
                        break
                    db.execute('DELETE FROM responses WHERE request_key=?', (oldest[0],))
                    total -= oldest[1]
        except sqlite3.Error:
            return


def _set_cooldown(seconds):
    global _in_memory_cooldown
    until = time.time() + seconds
    _in_memory_cooldown = max(_in_memory_cooldown, until)
    db = _db()
    if db is None:
        return
    with closing(db):
        try:
            with db:
                previous = db.execute('SELECT value FROM state WHERE name=?', ('blocked_until',)).fetchone()
                db.execute('INSERT OR REPLACE INTO state(name,value) VALUES (?,?)',
                           ('blocked_until', max(until, previous[0] if previous else 0)))
        except sqlite3.Error:
            return


def _cooldown_seconds():
    until = _in_memory_cooldown
    db = _db()
    if db is not None:
        with closing(db):
            try:
                row = db.execute('SELECT value FROM state WHERE name=?', ('blocked_until',)).fetchone()
                if row:
                    until = max(until, row[0])
            except sqlite3.Error:
                pass
    return max(0, math.ceil(until - time.time()))


def _retry_after_seconds(value):
    """Retry-After can be a delay in seconds or an HTTP date."""
    if value:
        value = str(value).strip()
        try:
            seconds = int(value)
        except ValueError:
            try:
                when = parsedate_to_datetime(value)
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
                seconds = math.ceil((when - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                seconds = DEFAULT_RATE_LIMIT_SECONDS
        if seconds > 0:
            return min(seconds, MAX_RETRY_AFTER_SECONDS)
    return DEFAULT_RATE_LIMIT_SECONDS


def _rate_limit_message(seconds):
    minutes = max(1, math.ceil(seconds / 60))
    return (f'Internet Archive rate limit (HTTP 429). '
            f'Please wait about {minutes} minute(s) before trying again. '
            'Cached results can still be used. Do not repeatedly click Revive.')

def _allowed_archive_url(url: str) -> bool:
    """Redirects may target only known Internet Archive API/replay paths."""
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or parsed.username or parsed.password
                or parsed.port not in (None, 443)):
            return False
        if parsed.hostname == 'web.archive.org':
            return parsed.path.startswith(('/web/', '/cdx/search/cdx'))
        if parsed.hostname in ('archive.org', 'www.archive.org'):
            return parsed.path == '/wayback/available'
    except ValueError:
        return False
    return False


def _get(url, *, params=None, limit=MAX_RESOURCE):
    """Fetch bounded Archive bytes; reuse cached success and honor HTTP 429.

    Never automatically retry a 429. Validate each redirect so an archived
    response cannot send the server to an arbitrary external host.
    """
    if not _allowed_archive_url(url):
        raise ArchiveError('Blocked non-Archive request URL.')

    key = _request_key(url, params)
    cached = _cached_response(key)
    if cached is not None:
        if len(cached[0]) > limit:
            raise ArchiveError('Cached archive response exceeds allowed size.')
        return cached

    cooldown = _cooldown_seconds()
    if cooldown:
        raise ArchiveRateLimited(_rate_limit_message(cooldown))

    current = url
    for redirect_number in range(6):
        try:
            with requests.get(current, params=params if redirect_number == 0 else None,
                              allow_redirects=False, timeout=(10, 30), stream=True,
                              headers=HEADERS) as resp:
                if resp.status_code == 429:
                    seconds = _retry_after_seconds(resp.headers.get('Retry-After'))
                    _set_cooldown(seconds)
                    raise ArchiveRateLimited(_rate_limit_message(seconds))
                if resp.status_code == 403:
                    raise ArchiveError('Internet Archive denied access (HTTP 403).')
                if resp.status_code in (301, 302, 303, 307, 308):
                    target = urljoin(current, resp.headers.get('location', ''))
                    if not _allowed_archive_url(target):
                        raise ArchiveError('Wayback redirected outside approved Archive endpoints.')
                    current = target
                    continue
                resp.raise_for_status()
                chunks = []
                size = 0
                for chunk in resp.iter_content(chunk_size=32768):
                    size += len(chunk)
                    if size > limit:
                        raise ArchiveError('Archived resource exceeds allowed size.')
                    chunks.append(chunk)
                body = b''.join(chunks)
                content_type = resp.headers.get('content-type', '')
                _cache_success(key, body, content_type, url)
                return body, content_type
        except requests.RequestException as exc:
            raise ArchiveError('Internet Archive request failed: ' + str(exc)) from exc
    raise ArchiveError('Wayback sent too many redirects.')


def _snapshot_from_availability(original_url: str, year: int | None):
    """Ask the official availability API for a close capture (no CDX needed).

    A selected year must match exactly: never silently redesign a 2018 page
    when the user requested 2010.
    """
    import json
    from urllib.parse import urlunsplit

    variations = [original_url]
    parsed = urlsplit(original_url)
    # Early Wayback captures commonly used HTTP rather than HTTPS.
    if parsed.scheme == 'https':
        variations.insert(0, urlunsplit(('http', parsed.netloc, parsed.path, parsed.query, parsed.fragment)))

    for candidate in variations:
        params = {'url': candidate}
        if year is not None:
            params['timestamp'] = f'{int(year):04d}0701'
        raw, _ = _get(AVAILABILITY, params=params, limit=100_000)
        try:
            entry = json.loads(raw).get('archived_snapshots', {}).get('closest', {})
        except (ValueError, TypeError, AttributeError) as exc:
            raise ArchiveError('Wayback Availability API returned invalid JSON.') from exc
        if not entry.get('available') or str(entry.get('status', '200')) != '200':
            continue
        timestamp = str(entry.get('timestamp', ''))
        if len(timestamp) != 14 or not timestamp.isdigit():
            continue
        if year is not None and timestamp[:4] != str(year):
            continue
        # Extract the *original captured URL* from the official replay link.
        replay = str(entry.get('url', ''))
        match = re.match(r'^https?://web\.archive\.org/web/\d{14}(?:[a-z_]+)?/(https?://.+)$', replay)
        captured_url = match.group(1) if match else candidate
        try:
            source = urlsplit(captured_url)
            requested = urlsplit(original_url)
            if (source.scheme not in ('http', 'https')
                or source.hostname != requested.hostname
                or source.username or source.password
                or source.port not in (None, 80, 443)):
                captured_url = candidate
        except ValueError:
            captured_url = candidate
        return {
            'timestamp': timestamp,
            'year': timestamp[:4],
            'archive_url': f'{WAYBACK}/web/{timestamp}/{captured_url}',
            'original_url': captured_url,
            'requested_url': original_url,
        }
    return None


def _snapshot_from_cdx(original_url: str, year: int):
    import json
    from urllib.parse import urlunsplit

    variants = [original_url]
    parsed = urlsplit(original_url)
    if parsed.scheme == 'https':
        variants.insert(0, urlunsplit(('http', parsed.netloc, parsed.path, parsed.query, parsed.fragment)))
    for candidate in variants:
        data, _ = _get(CDX, params={
            'url': candidate, 'output': 'json', 'filter': 'statuscode:200',
            'from': str(year), 'to': str(year), 'collapse': 'timestamp:4',
            'fl': 'timestamp,original', 'limit': '12'
        }, limit=200_000)
        try:
            rows = json.loads(data)
            if not isinstance(rows, list) or len(rows) < 2:
                continue
            timestamp, captured_url = str(rows[1][0]), str(rows[1][1])
        except (ValueError, TypeError, IndexError, AttributeError) as exc:
            raise ArchiveError('Wayback CDX response is invalid.') from exc
        if len(timestamp) != 14 or not timestamp.isdigit() or timestamp[:4] != str(year):
            continue
        source, requested = urlsplit(captured_url), urlsplit(original_url)
        if (source.scheme not in ('http', 'https') or source.hostname != requested.hostname
            or source.username or source.password or source.port not in (None, 80, 443)):
            continue
        return {'timestamp': timestamp, 'year': timestamp[:4],
                'archive_url': f'{WAYBACK}/web/{timestamp}/{captured_url}',
                'original_url': captured_url, 'requested_url': original_url}
    return None


def find_snapshot(original_url: str, year: int | None = None) -> dict | None:
    original_url = validate_public_url(original_url)
    if year is not None and not (1996 <= int(year) <= 2100):
        raise ArchiveError('Invalid archive year.')

    # Availability is typically more responsive than CDX and accepts a timestamp.
    # Retry via CDX only if Availability cannot find a capture from that year.
    api_error = None
    try:
        result = _snapshot_from_availability(original_url, year)
        if result is not None:
            return result
    except ArchiveRateLimited:
        # Do not immediately query CDX after an explicit rate limit.
        raise
    except ArchiveError as exc:
        api_error = exc

    if year is None:
        if api_error:
            raise ArchiveError('Cannot reach the Wayback Availability API. '
                               'Test https://archive.org/wayback/available in your browser. '
                               f'Details: {api_error}') from api_error
        return None

    try:
        return _snapshot_from_cdx(original_url, int(year))
    except ArchiveRateLimited:
        raise
    except ArchiveError as cdx_error:
        raise ArchiveError(
            'Could not contact the Internet Archive APIs. '
            'Please test web.archive.org and archive.org from your browser, '
            'or try a different internet connection. '
            f'Availability: {api_error or "no matching capture in selected year"}. '
            f'CDX: {cdx_error}'
        ) from cdx_error


def _raw(timestamp, url):
    return f'{WAYBACK}/web/{timestamp}id_/{url}'


def _decode(raw, content_type=''):
    match = re.search(r'charset\s*=\s*["\']?([\w-]+)',content_type,re.I)
    if not match:
        match = re.search(rb'<meta[^>]*charset=["\']?([\w-]+)',raw[:5000],re.I)
        if match: encoding = match.group(1).decode('ascii','ignore')
        else: encoding = 'utf-8'
    else: encoding = match.group(1)
    try: return raw.decode(encoding,errors='replace')
    except LookupError: return raw.decode('utf-8',errors='replace')


def _same_host(url, base):
    a,b = urlsplit(url),urlsplit(base)
    return a.scheme in ('http','https') and a.hostname==b.hostname and (a.port or None)==(b.port or None)


def _ext(url):
    from pathlib import PurePosixPath
    return PurePosixPath(urlsplit(url).path).suffix.lower()


def _local_name(url, base, page=False):
    key = hashlib.sha256(url.encode()).hexdigest()[:12]
    if page and url.rstrip('/')==base.rstrip('/'):
        return 'index.html'
    if page:
        return f'pages/page-{key}.html'
    ext = _ext(url)
    if ext not in IMG_EXT | CSS_EXT | FONTS:
        ext='.bin'
    return f'assets/archived-{key}{ext}'


def _capture_information(snapshot: dict) -> dict:
    """Provenance from the Wayback lookup, not an assertion about every asset."""
    timestamp = str(snapshot.get('timestamp', ''))
    try:
        captured_at = datetime.strptime(timestamp, '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
    except (ValueError, TypeError) as exc:
        raise ArchiveError('Wayback returned an invalid snapshot timestamp.') from exc
    requested = snapshot.get('requested_year')
    return {
        'timestamp': timestamp,
        'date_utc': captured_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'year': captured_at.year,
        'requested_year': int(requested) if requested is not None else None,
        'original_url': str(snapshot.get('original_url', '')),
        'archive_url': str(snapshot.get('archive_url', '')),
        'provenance_note': (
            'Timestamp selected by Wayback lookup for the main snapshot. '
            'Redirected captures and individual archived assets may have different dates.'
        ),
    }


def recover_archived_site(snapshot: dict) -> SiteBundle:
    """Recover a bounded subset of a site and *report* discovered/failed work.

    Coverage describes URLs found in fetched documents only; it is NOT the
    percentage of an entire historical site recovered.
    """
    base = snapshot['original_url']
    timestamp = snapshot['timestamp']
    capture = _capture_information(snapshot)
    files = {}
    page_html = {}
    url_to_path = {}
    warnings = []
    visited = set()
    attempted_pages = set()
    discovered_pages = {base}
    failed_pages = {}
    queue = deque([base])
    asset_urls = set()
    discovered_assets = set()
    attempted_assets = set()
    failed_assets = {}
    external_assets = set()
    total_bytes = 0
    rate_limited = False
    page_queue_truncated = False
    asset_queue_truncated = False

    # Cap total attempts, including failures, not just successful HTML pages.
    while queue and len(attempted_pages) < MAX_PAGES:
        url = queue.popleft()
        if url in visited or not _same_host(url, base):
            continue
        visited.add(url)
        attempted_pages.add(url)
        try:
            raw, ct = _get(_raw(timestamp, url), limit=MAX_RESOURCE)
            if 'html' not in ct.lower() and not raw[:120].lstrip().lower().startswith((b'<!doctype html', b'<html')):
                failed_pages[url] = 'No HTML capture returned'
                warnings.append(f'No HTML snapshot available: {url}')
                continue
        except ArchiveRateLimited as exc:
            failed_pages[url] = 'Wayback rate limit (HTTP 429)'
            if not page_html:
                raise
            warnings.append(f'Archive access paused; remaining pages were not fetched: {exc}')
            rate_limited = True
            break
        except ArchiveError as exc:
            failed_pages[url] = str(exc)
            warnings.append(f'Could not recover page: {url} — {exc}')
            continue
        if total_bytes + len(raw) > MAX_BYTES:
            failed_pages[url] = 'Total archive size limit reached'
            warnings.append('Archive limit reached (20 MB).')
            page_queue_truncated = True
            break
        total_bytes += len(raw)
        local = _local_name(url, base, page=True)
        page_html[url] = _decode(raw, ct)
        url_to_path[url] = local
        soup = BeautifulSoup(page_html[url], 'html.parser')
        for a in soup.find_all('a', href=True):
            href = str(a.get('href', '')).strip()
            if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
                continue
            found = urldefrag(urljoin(url, href))[0]
            if _same_host(found, base) and _ext(found) in HTML_LIKE:
                discovered_pages.add(found)
                if found not in visited and found not in queue:
                    if len(queue) < 100:
                        queue.append(found)
                    else:
                        page_queue_truncated = True
        for tag, attr in [('img', 'src'), ('link', 'href')]:
            for item in soup.find_all(tag):
                ref = item.get(attr)
                if not ref:
                    continue
                asset = urldefrag(urljoin(url, str(ref)))[0]
                if _ext(asset) not in (IMG_EXT | CSS_EXT | FONTS):
                    continue
                if _same_host(asset, base):
                    asset_urls.add(asset)
                    discovered_assets.add(asset)
                elif urlsplit(asset).scheme in ('http', 'https'):
                    external_assets.add(asset)

    if not page_html:
        detail = warnings[0] if warnings else 'No archived HTML was returned.'
        raise ArchiveError('No HTML could be recovered for this snapshot. ' + detail
                           + ' Try another archive year or the original HTTP URL.')
    if queue or page_queue_truncated:
        warnings.append('Page crawl limited by safety caps; some discovered pages were not fetched.')

    asset_pending = deque(sorted(asset_urls))
    queued_assets = set(asset_pending)
    asset_map = {}
    asset_ct = {}
    while asset_pending and len(attempted_assets) < MAX_ASSETS and not rate_limited:
        url = asset_pending.popleft()
        queued_assets.discard(url)
        if url in attempted_assets or not _same_host(url, base):
            continue
        attempted_assets.add(url)
        try:
            raw, ct = _get(_raw(timestamp, url), limit=MAX_RESOURCE)
        except ArchiveRateLimited as exc:
            failed_assets[url] = 'Wayback rate limit (HTTP 429)'
            warnings.append(f'Archive access paused; remaining assets were not fetched: {exc}')
            rate_limited = True
            break
        except ArchiveError as exc:
            failed_assets[url] = str(exc)
            warnings.append(f'Missing archived asset: {url}')
            continue
        if total_bytes + len(raw) > MAX_BYTES:
            failed_assets[url] = 'Total archive size limit reached'
            warnings.append('Asset size limit reached (20 MB).')
            asset_queue_truncated = True
            break
        if 'text/html' in ct.lower() and _ext(url) not in ('.html', '.htm'):
            failed_assets[url] = 'Archive returned an HTML page instead of this asset'
            warnings.append(f'Archive did not return the expected asset: {url}')
            continue
        total_bytes += len(raw)
        local = _local_name(url, base)
        asset_map[url] = local
        asset_ct[url] = ct
        files[local] = raw
        if _ext(url) == '.css':
            text = _decode(raw, ct)
            for match in re.finditer(r'url\(\s*["\']?([^"\')]+)', text, re.I):
                ref = match.group(1).strip()
                child = urldefrag(urljoin(url, ref))[0]
                if _ext(child) not in (IMG_EXT | FONTS):
                    continue
                if _same_host(child, base):
                    discovered_assets.add(child)
                    if child not in asset_map and child not in queued_assets and child not in attempted_assets:
                        asset_pending.append(child)
                        queued_assets.add(child)
                elif urlsplit(child).scheme in ('http', 'https'):
                    external_assets.add(child)
    if asset_pending or asset_queue_truncated:
        warnings.append('Some discovered assets were not fetched (limit, size or access restriction).')
    if external_assets:
        warnings.append(f'{len(external_assets)} off-host asset reference(s) were not downloaded.')

    # Re-link only assets and pages that were ACTUALLY retrieved.
    for url, markup in page_html.items():
        local = url_to_path[url]
        soup = BeautifulSoup(markup, 'html.parser')
        for a in soup.find_all('a', href=True):
            target = urldefrag(urljoin(url, a['href']))[0]
            if target in url_to_path:
                a['href'] = posixpath.relpath(url_to_path[target], posixpath.dirname(local) or '.')
        for tag, attr in [('img', 'src'), ('link', 'href')]:
            for item in soup.find_all(tag):
                ref = item.get(attr)
                if not ref:
                    continue
                target = urldefrag(urljoin(url, ref))[0]
                if target in asset_map:
                    item[attr] = posixpath.relpath(asset_map[target], posixpath.dirname(local) or '.')
        files[local] = str(soup).encode('utf-8')
    for url, local in asset_map.items():
        if _ext(url) != '.css':
            continue
        text = _decode(files[local], asset_ct[url])
        def sub_asset(m):
            ref = m.group(2)
            target = urldefrag(urljoin(url, ref))[0]
            if target in asset_map:
                new = posixpath.relpath(asset_map[target], posixpath.dirname(local) or '.')
                return f'url("{new}")'
            return 'url("")'
        text = re.sub(r'url\(\s*(["\']?)(.*?)\1\s*\)', sub_asset, text, flags=re.I)
        files[local] = text.encode('utf-8')

    homepage = url_to_path.get(base)
    if not homepage or homepage not in files:
        homepage = sorted(p for p in files if p.endswith('.html'))[0]

    # Truncated lists stay truthful through the full integer counts.
    not_attempted_pages = sorted(discovered_pages - attempted_pages)
    not_attempted_assets = sorted(discovered_assets - attempted_assets)
    image_urls = {u for u in discovered_assets if _ext(u) in IMG_EXT}
    recovery = {
        'capture': capture,
        'pages': {
            'discovered': len(discovered_pages),
            'attempted': len(attempted_pages),
            'recovered': len(page_html),
            'failed': len(failed_pages),
            'not_attempted': len(not_attempted_pages),
            'failed_urls': [{'url': u, 'reason': e} for u, e in sorted(failed_pages.items())[:30]],
            'not_attempted_urls': not_attempted_pages[:30],
        },
        'assets': {
            'discovered': len(discovered_assets),
            'attempted': len(attempted_assets),
            'recovered': len(asset_map),
            'failed': len(failed_assets),
            'not_attempted': len(not_attempted_assets),
            'image_urls_discovered': len(image_urls),
            'image_urls_recovered': sum(u in asset_map for u in image_urls),
            'external_not_downloaded': len(external_assets),
            'failed_urls': [{'url': u, 'reason': e} for u, e in sorted(failed_assets.items())[:30]],
            'not_attempted_urls': not_attempted_assets[:30],
            'external_examples': sorted(external_assets)[:15],
        },
        'limits': {'max_pages': MAX_PAGES, 'max_assets': MAX_ASSETS, 'max_total_bytes': MAX_BYTES},
        'rate_limited': rate_limited,
        'coverage_note': (
            'Counts describe references discovered in retrieved HTML/CSS only, not '
            'all historical website pages. Off-host resources, scripts and dynamic '
            'backends are outside this bounded recovery. Zero broken LOCAL links '
            'does not prove archived resources are complete.'
        ),
    }
    warnings.append('Wayback recovery is best-effort; missing pages, external resources and dynamic backends cannot be restored automatically.')
    return SiteBundle(files, homepage, source='wayback', source_url=base,
                      warnings=warnings, recovery=recovery)
