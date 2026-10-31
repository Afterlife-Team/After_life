"""Offline tests for truthful Wayback dates/coverage; never call live archive."""
import pytest
from services import archive_site as archive
from services.redesign import modernize_site

BASE = 'https://old.example/'
CAPTURE = {'original_url': BASE, 'timestamp': '20051010010101',
           'archive_url': 'https://web.archive.org/web/20051010010101/https://old.example/',
           'requested_year': 2005}


def mock_replay(monkeypatch, responses):
    calls = []
    def fake_get(url, **kwargs):
        assert '/web/' in url and 'id_/' in url
        original = url.split('id_/', 1)[1]
        calls.append(original)
        if original not in responses:
            raise archive.ArchiveError('Archive capture missing')
        return responses[original]
    monkeypatch.setattr(archive, '_get', fake_get)
    return calls


def test_date_and_missing_page_asset_are_reported(monkeypatch):
    responses = {
        BASE: (b'''<html><head><link rel="stylesheet" href="style.css"></head><body>
             <a href="about.html">About</a><a href="lost.html">Lost</a>
             <img src="images/good.png"><img src="images/missing.png">
             <img src="https://cdn.example.com/picture.jpg"></body></html>''', 'text/html'),
        BASE+'about.html': (b'<html><body><p>About</p></body></html>', 'text/html'),
        BASE+'style.css': (b'body{background:url(images/missing2.jpg)}', 'text/css'),
        BASE+'images/good.png': (b'png-data', 'image/png'),
    }
    mock_replay(monkeypatch, responses)
    bundle = archive.recover_archived_site(CAPTURE)
    report = bundle.recovery
    assert report['capture']['date_utc'] == '2005-10-10 01:01:01 UTC'
    assert report['capture']['requested_year'] == 2005
    assert (report['pages']['discovered'], report['pages']['attempted'],
            report['pages']['recovered'], report['pages']['failed'],
            report['pages']['not_attempted']) == (3, 3, 2, 1, 0)
    assert any('lost.html' in x['url'] for x in report['pages']['failed_urls'])
    assert report['assets']['discovered'] == 4
    assert report['assets']['recovered'] == 2
    assert report['assets']['failed'] == 2
    assert report['assets']['external_not_downloaded'] == 1
    assert report['assets']['image_urls_discovered'] == 3
    assert report['assets']['image_urls_recovered'] == 1
    assert bundle.copy_with(dict(bundle.files)).recovery == report
    assert modernize_site(bundle).recovery == report


def test_discovered_unattempted_pages_when_capped(monkeypatch):
    links = ''.join(f'<a href="page{i}.html">P{i}</a>' for i in range(16))
    responses = {BASE: (('<html><body>' + links + '</body></html>').encode(), 'text/html')}
    for i in range(16):
        responses[BASE+f'page{i}.html'] = (b'<html><body>OK</body></html>', 'text/html')
    calls = mock_replay(monkeypatch, responses)
    bundle = archive.recover_archived_site(CAPTURE)
    report = bundle.recovery['pages']
    assert report['discovered'] == 17
    assert report['attempted'] == archive.MAX_PAGES
    assert report['recovered'] == archive.MAX_PAGES
    assert report['not_attempted'] == 5
    assert len(calls) == archive.MAX_PAGES


def test_partial_recovery_reports_429_without_continuing(monkeypatch):
    calls = []
    def fake_get(url, **kwargs):
        original = url.split('id_/', 1)[1]
        calls.append(original)
        if original == BASE:
            return (b'<html><body><a href="next.html">Next</a><img src="img.png"></body></html>', 'text/html')
        raise archive.ArchiveRateLimited('HTTP 429')
    monkeypatch.setattr(archive, '_get', fake_get)
    bundle = archive.recover_archived_site(CAPTURE)
    assert calls == [BASE, BASE+'next.html']
    assert bundle.recovery['rate_limited'] is True
    assert bundle.recovery['pages']['failed'] == 1
    assert bundle.recovery['assets']['not_attempted'] == 1
    assert bundle.recovery['assets']['attempted'] == 0


def test_invalid_archive_timestamp_rejected_before_network(monkeypatch):
    monkeypatch.setattr(archive, '_get', lambda *a, **kw: pytest.fail('No networking expected'))
    with pytest.raises(archive.ArchiveError, match='timestamp'):
        archive.recover_archived_site({'original_url': BASE, 'timestamp': '20260230000000'})
