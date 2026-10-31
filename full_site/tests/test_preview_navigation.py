import base64
import json
import re
from services.site_bundle import SiteBundle
from services.preview import preview_page
from services.preview_navigation import navigable_preview
from bs4 import BeautifulSoup


def site():
    return SiteBundle({'index.html':b'<html><body><h1>Home</h1><a href="about.html#detail">About</a><a href="https://example.com/" target="_top">Online</a><script>parent.PWNED=1</script></body></html>',
                       'about.html':b'<html><body><h1 id="detail">About</h1><a href="index.html">Home</a></body></html>'},'index.html')


def test_internal_navigation_is_sanitized_and_opt_in():
    original=site()
    default=BeautifulSoup(preview_page(original,'index.html'),'html.parser')
    assert not default.find('a',string='About').has_attr('href')
    enabled=BeautifulSoup(preview_page(original,'index.html',internal_navigation=True),'html.parser')
    link=enabled.find('a',string='About')
    assert link['data-afterlife-page']=='about.html'
    assert link['data-afterlife-fragment']=='detail'
    assert link['href']=='#'
    assert not enabled.find('script')
    assert enabled.find('a',string='Online')['target']=='_blank'


def test_attacker_cannot_forge_navigation_marker():
    bundle=SiteBundle({'index.html':b'<a href="javascript:alert(1)" data-afterlife-page="https://evil.example" data-afterlife-fragment="bad">Fake</a>'},'index.html')
    soup=BeautifulSoup(preview_page(bundle,'index.html',internal_navigation=True),'html.parser')
    assert not soup.a.has_attr('data-afterlife-page')
    assert not soup.a.has_attr('href')


def test_shell_contains_only_sanitized_pages_and_script_disabled_frame():
    shell=navigable_preview(site(),'index.html')
    soup=BeautifulSoup(shell,'html.parser')
    assert 'allow-scripts' not in soup.iframe['sandbox']
    assert 'allow-same-origin' in soup.iframe['sandbox']
    encoded=re.search("atob\\('([^']+)'\\)",shell).group(1)
    payload=json.loads(base64.b64decode(encoded))
    assert set(payload['pages'])=={'index.html','about.html'}
    assert all('PWNED' not in p for p in payload['pages'].values())
    assert all("script-src 'none'" in p for p in payload['pages'].values())
