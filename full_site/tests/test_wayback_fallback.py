"""Run with: python -m pytest -q tests/test_wayback_fallback.py"""
from services import archive_site


def test_availability_first_for_selected_year(monkeypatch):
    monkeypatch.setattr(archive_site, 'validate_public_url', lambda url: url)
    called = []

    def fake_get(url, **kwargs):
        called.append((url, kwargs.get('params')))
        assert 'archive.org/wayback/available' in url
        return (b'{"archived_snapshots":{"closest":{"available":true,"status":"200",'
                b'"timestamp":"20100701010101",'
                b'"url":"http://web.archive.org/web/20100701010101/http://www.wikipedia.org/"}}}',
                'application/json')

    monkeypatch.setattr(archive_site, '_get', fake_get)
    result = archive_site.find_snapshot('https://www.wikipedia.org', 2010)
    assert result['year'] == '2010'
    assert result['original_url'] == 'http://www.wikipedia.org/'
    assert len(called) == 1
    assert called[0][1]['timestamp'] == '20100701'


def test_cdx_used_if_availability_returns_different_year(monkeypatch):
    monkeypatch.setattr(archive_site, 'validate_public_url', lambda url: url)
    called = []

    def fake_get(url, **kwargs):
        called.append(url)
        if '/wayback/available' in url:
            return (b'{"archived_snapshots":{"closest":{"available":true,"status":"200",'
                    b'"timestamp":"20180101010101",'
                    b'"url":"http://web.archive.org/web/20180101010101/http://www.wikipedia.org/"}}}',
                    'application/json')
        return (b'[["timestamp","original"],["20100801010101","http://www.wikipedia.org/"]]',
                'application/json')

    monkeypatch.setattr(archive_site, '_get', fake_get)
    result = archive_site.find_snapshot('https://www.wikipedia.org', 2010)
    assert result['year'] == '2010'
    assert len(called) >= 2


def test_apis_both_timeout_reports_network(monkeypatch):
    monkeypatch.setattr(archive_site, 'validate_public_url', lambda url: url)

    def fake_get(url, **kwargs):
        raise archive_site.ArchiveError('ConnectTimeout')

    monkeypatch.setattr(archive_site, '_get', fake_get)
    try:
        archive_site.find_snapshot('https://www.wikipedia.org', 2010)
        assert False, 'expected error'
    except archive_site.ArchiveError as exc:
        assert 'internet connection' in str(exc)
