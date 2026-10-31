from services.archive_site import recover_archived_site, find_snapshot, ArchiveError
from services.analysis import analyze_site
from services.preview import preview_page


def test_mock_wayback_crawls_pages_and_static_assets(monkeypatch):
    from services import archive_site
    base='https://old.example/'
    responses={
      'https://old.example/':(b'<html><head><link rel="stylesheet" href="css/style.css"></head><body><h1>Retro</h1><a href="about.html">About</a><img src="images/logo.png"></body></html>','text/html'),
      'https://old.example/about.html':(b'<html><body><h1>About Retro</h1><a href="/">Back</a></body></html>','text/html'),
      'https://old.example/css/style.css':(b'body{color:#123456;background:url("../images/logo.png")}','text/css'),
      'https://old.example/images/logo.png':(b'\x89PNG\r\n\x1a\n','image/png'),
    }
    def fake_get(url,**kwargs):
        if 'id_/' not in url: raise AssertionError('Unexpected URL '+url)
        original=url.split('id_/',1)[1]
        if original not in responses: raise ArchiveError('missing')
        return responses[original]
    monkeypatch.setattr(archive_site,'_get',fake_get)
    s=recover_archived_site({'original_url':base,'timestamp':'20051010010101'})
    assert len(s.pages)==2
    assert s.homepage=='index.html'
    assert len(s.files)==4
    report=analyze_site(s)
    assert '#123456' in report['colors']
    assert not report['missing_references']
    assert 'data:image/png;base64' in preview_page(s,'index.html')
    assert 'href="pages/' in s.files['index.html'].decode('utf-8')


def test_mock_cdx_year_and_auto(monkeypatch):
    from services import archive_site
    monkeypatch.setattr(archive_site,'validate_public_url',lambda u:u)
    def fake_get(url,**kwargs):
        if 'cdx' in url:
            return b'[["timestamp","original"],["20051115010203","https://old.example/"]]','application/json'
        return b'{"archived_snapshots":{"closest":{"available":true,"timestamp":"20100102030405"}}}','application/json'
    monkeypatch.setattr(archive_site,'_get',fake_get)
    assert find_snapshot('https://old.example/',2005)['year']=='2005'
    assert find_snapshot('https://old.example/')['year']=='2010'
