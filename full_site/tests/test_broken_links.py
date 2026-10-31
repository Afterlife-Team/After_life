from bs4 import BeautifulSoup
import pytest
from services.archive_site import _rewrite_page_links, recover_archived_site
from services.analysis import analyze_site
from services.site_bundle import SiteBundle,resolve_local,to_zip,site_from_zip

BASE='https://old.example/dir/index.html'
STAMP='20200102030405'


def test_archived_links_keep_fragments_and_missing_pages_go_online():
    soup=BeautifulSoup('<a href="next.html#section">Next</a><a href="#here">Here</a><a href="lost.html?q=1#part">Lost</a>','html.parser')
    mapping={BASE:'index.html','https://old.example/dir/next.html':'pages/next.html'}
    online=_rewrite_page_links(soup,BASE,'index.html',mapping,STAMP,lambda t,u:f'https://arquivo.pt/wayback/{t}/{u}')
    anchors=soup.find_all('a')
    assert anchors[0]['href']=='pages/next.html#section'
    assert anchors[1]['href']=='#here'
    assert anchors[2]['href']==f'https://arquivo.pt/wayback/{STAMP}/https://old.example/dir/lost.html?q=1#part'
    assert anchors[2]['data-afterlife-online-archive']=='true'
    assert len(online)==1 and anchors[2].get_text()=='Lost'


def test_protocol_relative_external_link_keeps_its_real_destination():
    soup=BeautifulSoup('<a href="//other.example/path#x">Other</a><a href="mailto:test@example.com">Mail</a>','html.parser')
    _rewrite_page_links(soup,BASE,'index.html',{BASE:'index.html'},STAMP,lambda t,u:u)
    assert soup.a['href']=='https://other.example/path#x'
    assert soup.find_all('a')[1]['href']=='mailto:test@example.com'


@pytest.mark.parametrize('ref,current,expected',[
    ('/','docs/page.html','index.html'),('?q=1','docs/page.html','docs/page.html'),
    ('../','docs/page.html','index.html'),('docs/','index.html','docs/index.html')])
def test_directory_and_query_links_resolve(ref,current,expected):
    files={p:b'' for p in ('index.html','docs/page.html','docs/index.html')}
    assert resolve_local(ref,current,files)==expected


def test_analyzer_checks_named_and_encoded_anchors():
    files={'index.html':b'<html><body><a name="old"></a><h2 id="a b">Title</h2><a href="#old">One</a><a href="#a%20b">Two</a><a href="#missing">Bad</a><a href="child.html#lost">Other</a><a href="#top">Top</a></body></html>',
           'child.html':b'<html><body>Child</body></html>'}
    report=analyze_site(SiteBundle(files,'index.html'))
    assert report['link_issue_count']==2
    assert {issue['href'] for issue in report['link_issues']}=={'#missing','child.html#lost'}
    assert all(issue['reason']=='missing_anchor' for issue in report['link_issues'])


def test_analyzer_does_not_crash_on_malformed_link():
    site=SiteBundle({'index.html':b'<a href="http://[bad">Bad</a>'},'index.html')
    assert analyze_site(site)['link_issues'][0]['reason']=='invalid_url'


def test_recovered_export_has_no_relative_link_to_unrecovered_page():
    responses={BASE:(b'<html><body><h1 id="main">Home</h1><a href="next.html#detail">Next</a><a href="lost.html">Lost</a></body></html>','text/html'),
               'https://old.example/dir/next.html':(b'<html><body><h2 id="detail">Detail</h2><a href="index.html#main">Home</a></body></html>','text/html')}
    def fetch(stamp,url):
        from services.archive_site import ArchiveError
        if url not in responses: raise ArchiveError('Not archived')
        return responses[url]
    bundle=recover_archived_site({'timestamp':STAMP,'original_url':BASE},fetch_resource=fetch)
    exported=site_from_zip(to_zip(bundle))
    report=analyze_site(exported)
    assert report['missing_references']==[]
    assert report['online_archive_link_count']==1
    assert bundle.recovery['online_archive_links']['count']==1
    assert 'web.archive.org/web/' in exported.files['index.html'].decode()
    assert '#detail' in exported.files['index.html'].decode()
