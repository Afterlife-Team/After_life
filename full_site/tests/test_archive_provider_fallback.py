import json
import pytest
from services import arquivo, archive_site as wayback, archive_fallback as flow
from services.site_bundle import SiteBundle, site_from_zip, to_zip
from services.security import UnsafeURL

URL='https://old.example/index.html'
STAMP='20200102030405'


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch,tmp_path):
    monkeypatch.setattr(wayback,'CACHE_DB',tmp_path/'cache.sqlite3')
    monkeypatch.setattr(wayback,'_in_memory_cooldown',0)
    monkeypatch.setattr(arquivo,'_blocked_until',0)
    monkeypatch.setattr(flow,'validate_public_url',lambda u:u)


def bundle():
    return SiteBundle({'index.html':b'<html>Original</html>'},'index.html',source='wayback',
                      recovery={'capture':{}})


def test_wayback_success_does_not_call_backup(monkeypatch):
    monkeypatch.setattr(wayback,'find_snapshot',lambda *a:{'timestamp':STAMP})
    original=bundle()
    monkeypatch.setattr(wayback,'recover_archived_site',lambda s:original)
    monkeypatch.setattr(arquivo,'find_snapshot',lambda *a:pytest.fail('No backup needed'))
    assert flow.recover_from_url(URL) is original
    assert original.recovery['capture']['provider'] == 'Wayback Machine'


@pytest.mark.parametrize('stage',['lookup','recovery','no_capture'])
def test_wayback_failure_tries_independent_backup(monkeypatch,stage):
    def lookup(*a):
        if stage=='lookup': raise wayback.ArchiveRateLimited('HTTP 429')
        return None if stage=='no_capture' else {'timestamp':STAMP}
    def recover(*a): raise wayback.ArchiveError('No HTML available')
    monkeypatch.setattr(wayback,'find_snapshot',lookup)
    monkeypatch.setattr(wayback,'recover_archived_site',recover)
    calls=[]
    monkeypatch.setattr(arquivo,'find_snapshot',lambda u,y:(calls.append((u,y)) or {'timestamp':STAMP}))
    result=bundle(); result.source='arquivo'
    monkeypatch.setattr(arquivo,'recover',lambda s:result)
    assert flow.recover_from_url(URL,2020) is result
    assert calls == [(URL,2020)]
    assert result.recovery['fallback']['used']


def test_both_fail_reports_both_without_claiming_success(monkeypatch):
    monkeypatch.setattr(wayback,'find_snapshot',lambda *a:None)
    monkeypatch.setattr(arquivo,'find_snapshot',lambda *a:None)
    with pytest.raises(wayback.ArchiveError,match='Wayback:.*Arquivo.pt:'):
        flow.recover_from_url(URL)


def test_unsafe_input_does_not_trigger_backup(monkeypatch):
    def unsafe(u): raise UnsafeURL('Local hosts blocked')
    monkeypatch.setattr(flow,'validate_public_url',unsafe)
    monkeypatch.setattr(arquivo,'find_snapshot',lambda *a:pytest.fail('Unsafe input'))
    with pytest.raises(UnsafeURL): flow.recover_from_url('http://localhost/')


def test_cdx_ndjson_year_and_tracking(monkeypatch):
    monkeypatch.setattr(arquivo,'validate_public_url',lambda u:u)
    row={'timestamp':STAMP,'url':URL,'status':'200','mime':'text/html'}
    def get(url,**kw):
        assert kw['params']['from']=='2020' and kw['params']['to']=='2020'
        assert kw['params']['url']==URL
        return json.dumps(row).encode(), 'text/x-ndjson'
    monkeypatch.setattr(arquivo,'_get',get)
    snapshot=arquivo.find_snapshot(URL+'?utm_source=test',2020)
    assert snapshot['provider']=='Arquivo.pt' and snapshot['timestamp']==STAMP


@pytest.mark.parametrize('changed',[
    {'timestamp':'20190102030405'}, {'url':'https://evil.example/index.html'},
    {'url':'https://old.example/other.html'}, {'timestamp':'not-a-date'},
    {'mime':'image/png'}, {'status':'404'}])
def test_cdx_rejects_wrong_capture(monkeypatch,changed):
    monkeypatch.setattr(arquivo,'validate_public_url',lambda u:u)
    row={'timestamp':STAMP,'url':URL,'status':'200','mime':'text/html',**changed}
    monkeypatch.setattr(arquivo,'_get',lambda *a,**kw:(json.dumps(row).encode(),''))
    assert arquivo.find_snapshot(URL,2020) is None


def test_backup_crawl_keeps_assets_and_provenance(monkeypatch):
    responses={URL:(b'<html><head><link rel="stylesheet" href="style.css"></head><body><h1>Original</h1><img src="logo.png"></body></html>','text/html'),
               'https://old.example/style.css':(b'body{color:#123456}','text/css'),
               'https://old.example/logo.png':(b'original-image','image/png')}
    def get(url,**kw):
        assert url.startswith(f'https://arquivo.pt/noFrame/replay/{STAMP}id_/')
        return responses[url.split('id_/',1)[1]]
    monkeypatch.setattr(arquivo,'_get',get)
    result=arquivo.recover({'timestamp':STAMP,'original_url':URL,'requested_year':2020,'archive_url':'https://arquivo.pt/wayback/'+STAMP+'/'+URL})
    assert result.source=='arquivo'
    assert result.recovery['capture']['provider']=='Arquivo.pt'
    assert result.recovery['assets']['recovered']==2
    assert any(raw==b'original-image' for raw in result.files.values())
    assert site_from_zip(to_zip(result)).files==result.files


class Response:
    status_code=200
    headers={'Content-Type':'text/html'}
    def __enter__(self): return self
    def __exit__(self,*a): pass
    def raise_for_status(self): pass
    def iter_content(self,**kw): yield b'<html>Backup</html>'


def test_wayback_cooldown_does_not_block_backup(monkeypatch):
    wayback._set_cooldown(300)
    monkeypatch.setattr(arquivo.requests,'get',lambda *a,**kw:Response())
    assert arquivo._get('https://arquivo.pt/wayback/cdx')[0]
    assert wayback._cooldown_seconds()>0


def test_backup_429_is_independent_and_cached_success_usable(monkeypatch):
    replay=f'https://arquivo.pt/noFrame/replay/{STAMP}id_/{URL}'
    monkeypatch.setattr(arquivo.requests,'get',lambda *a,**kw:Response())
    assert arquivo._get(replay)[0]
    response=Response(); response.status_code=429; response.headers={'Retry-After':'60'}
    monkeypatch.setattr(arquivo.requests,'get',lambda *a,**kw:response)
    with pytest.raises(wayback.ArchiveRateLimited): arquivo._get(arquivo.CDX)
    assert arquivo._cooldown()>0 and wayback._cooldown_seconds()==0
    assert arquivo._get(replay)[0]


def test_backup_blocks_external_redirects_and_oversize(monkeypatch):
    response=Response(); response.status_code=302; response.headers={'Location':'http://127.0.0.1/'}
    monkeypatch.setattr(arquivo.requests,'get',lambda *a,**kw:response)
    with pytest.raises(wayback.ArchiveError,match='outside'): arquivo._get(arquivo.CDX)
    monkeypatch.setattr(arquivo.requests,'get',lambda *a,**kw:Response())
    with pytest.raises(wayback.ArchiveError,match='size'): arquivo._get(arquivo.CDX,limit=2)


def test_streamlit_displays_backup_source_and_date(monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(arquivo,'_get',lambda *a,**kw:(b'<html><body><h1>Original archive</h1><p>Original content.</p></body></html>','text/html'))
    result=arquivo.recover({'timestamp':STAMP,'original_url':URL,'archive_url':'https://arquivo.pt/wayback/'+STAMP+'/'+URL})
    monkeypatch.setattr(flow,'recover_from_url',lambda *a:result)
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=20)
    app.radio[0].set_value('Recover from URL').run()
    app.text_input[0].set_value(URL)
    next(r for r in app.radio if r.label=='Redesign method').set_value('Safe CSS refresh (works now)')
    app.button[0].click().run(timeout=20)
    assert not app.exception and not app.error
    assert any('Arquivo.pt' in item.value for item in app.markdown)
    assert any('2020-01-02' in item.value for item in app.markdown)
