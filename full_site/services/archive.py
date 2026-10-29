import requests
from services.security import validate_public_url

AVAILABILITY_API = "https://archive.org/wayback/available"
CDX_API = "https://web.archive.org/cdx/search/cdx"
MAX_HTML_BYTES = 2_000_000
HEADERS = {"User-Agent": "404AfterlifeHackathon/1.0 (educational demo)"}

class ArchiveError(RuntimeError):
    pass

def _get(url, *, params=None):
    # No redirects: prevent silently following a redirect to a different host.
    try:
        response = requests.get(url, params=params, timeout=(5, 18),
                                allow_redirects=False, headers=HEADERS, stream=True)
        if response.status_code in (301, 302, 303, 307, 308):
            raise ArchiveError("Archive redirected; request blocked for safety.")
        response.raise_for_status()
        return response
    except requests.RequestException as exc:
        raise ArchiveError(f"Archive service unavailable: {exc}") from exc

def find_snapshot(original_url):
    original_url = validate_public_url(original_url)
    response = _get(AVAILABILITY_API, params={"url": original_url})
    try:
        payload = response.json()
    except ValueError as exc:
        raise ArchiveError("Archive returned invalid JSON.") from exc
    finally:
        response.close()
    snapshot = payload.get("archived_snapshots", {}).get("closest", {})
    if not snapshot.get("available") or not snapshot.get("url"):
        return None
    timestamp = str(snapshot.get("timestamp", ""))
    # Use the known Wayback host, not an arbitrary URL from a response.
    if not (timestamp.isdigit() and len(timestamp) == 14):
        raise ArchiveError("Archive timestamp is invalid.")
    return {"timestamp": timestamp, "year": timestamp[:4],
            "archive_url": f"https://web.archive.org/web/{timestamp}/{original_url}",
            "original_url": original_url}

def fetch_snapshot_html(snapshot):
    # id_ requests raw archived content rather than replay toolbar where supported.
    timestamp = snapshot["timestamp"]
    original_url = validate_public_url(snapshot["original_url"])
    url = f"https://web.archive.org/web/{timestamp}id_/{original_url}"
    response = _get(url)
    try:
        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type:
            raise ArchiveError("Archived response is not HTML.")
        chunks = []
        size = 0
        for chunk in response.iter_content(chunk_size=32768):
            size += len(chunk)
            if size > MAX_HTML_BYTES:
                raise ArchiveError("Archived HTML is too large (2 MB limit).")
            chunks.append(chunk)
        response._content = b"".join(chunks)
        return response.text
    finally:
        response.close()
