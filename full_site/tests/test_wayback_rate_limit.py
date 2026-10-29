"""No real internet calls. Run: python -m pytest tests/test_wayback_rate_limit.py -v"""
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import pytest
from services import archive_site as archive


class FakeResponse:
    def __init__(self, status, body=b'OK', headers=None):
        self.status_code = status
        self.body = body
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def iter_content(self, chunk_size=32768):
        yield self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise archive.requests.HTTPError(str(self.status_code))


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(archive, 'CACHE_DB', tmp_path / 'cache' / 'wayback.sqlite3')
    monkeypatch.setattr(archive, '_in_memory_cooldown', 0.0)


def test_cache_prevents_second_network_request(monkeypatch):
    network_calls = []
    def fake_get(*args, **kwargs):
        network_calls.append(args)
        return FakeResponse(200, b'{"archived_snapshots":{}}', {'content-type':'application/json'})
    monkeypatch.setattr(archive.requests, 'get', fake_get)
    first = archive._get(archive.AVAILABILITY, params={'url':'https://example.com'}, limit=100_000)
    second = archive._get(archive.AVAILABILITY, params={'url':'https://example.com'}, limit=100_000)
    assert first == second
    assert len(network_calls) == 1


def test_429_does_not_fall_through_to_cdx_and_persists_cooldown(monkeypatch):
    calls = []
    def fake_get(*args, **kwargs):
        calls.append(args)
        return FakeResponse(429, headers={'Retry-After':'120'})
    monkeypatch.setattr(archive.requests, 'get', fake_get)
    monkeypatch.setattr(archive, 'validate_public_url', lambda url: url)
    with pytest.raises(archive.ArchiveRateLimited, match='429'):
        archive.find_snapshot('https://www.wikipedia.org', 2010)
    assert len(calls) == 1
    # Even across a simulated module state reset the cooldown lives on disk.
    archive._in_memory_cooldown = 0
    with pytest.raises(archive.ArchiveRateLimited):
        archive.find_snapshot('https://www.wikipedia.org', 2010)
    assert len(calls) == 1
    assert archive._cooldown_seconds() >= 100


def test_cache_can_be_used_during_cooldown(monkeypatch):
    calls = []
    def fake_get(*args, **kwargs):
        calls.append(args)
        return FakeResponse(200, b'previously fetched', {'content-type':'text/html'})
    monkeypatch.setattr(archive.requests, 'get', fake_get)
    replay = 'https://web.archive.org/web/20100701010101id_/http://www.wikipedia.org/'
    assert archive._get(replay) == (b'previously fetched','text/html')
    archive._set_cooldown(300)
    assert archive._get(replay) == (b'previously fetched','text/html')
    assert len(calls) == 1
    with pytest.raises(archive.ArchiveRateLimited):
        archive._get('https://web.archive.org/web/20100701010101id_/http://www.wikipedia.org/about')
    assert len(calls) == 1


def test_retry_after_http_date():
    future = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=180))
    assert 170 <= archive._retry_after_seconds(future) <= 185
    assert archive._retry_after_seconds('300') == 300
    assert archive._retry_after_seconds(None) == 300


def test_redirect_outside_archive_is_blocked(monkeypatch):
    monkeypatch.setattr(archive.requests, 'get', lambda *args, **kwargs: FakeResponse(
        302, headers={'location':'http://127.0.0.1/admin'}))
    with pytest.raises(archive.ArchiveError, match='outside approved'):
        archive._get(archive.AVAILABILITY, params={'url':'https://example.com'})


def test_limit_still_applies_to_cache(monkeypatch):
    monkeypatch.setattr(archive.requests, 'get', lambda *args, **kwargs: FakeResponse(
        200, b'long response', {'content-type':'text/plain'}))
    archive._get(archive.CDX, params={'url':'https://example.com'}, limit=100)
    with pytest.raises(archive.ArchiveError, match='Cached archive response exceeds'):
        archive._get(archive.CDX, params={'url':'https://example.com'}, limit=3)
