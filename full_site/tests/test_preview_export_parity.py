from bs4 import BeautifulSoup
from services.preview import preview_page
from services.site_bundle import SiteBundle, to_zip, site_from_zip
from services.encoding import normalize_meta_utf8
from services.redesign import modernize_site
from services.ai_bridge import apply_ai_changes, AIIntegrationError
import pytest


def test_linked_inline_css_order_and_media_preserved():
    bundle = SiteBundle({'index.html': b'<html><head><style>h1{color:red}</style><link rel="stylesheet" href="theme.CSS" media="screen"><style>h1{color:green}</style><link rel="stylesheet" href="print.css" media="print"></head><body><h1>Hello</h1></body></html>',
        'theme.CSS': b'h1{color:blue}', 'print.css': b'h1{color:black}'}, 'index.html')
    soup = BeautifulSoup(preview_page(bundle,'index.html'),'html.parser')
    styles = soup.find_all('style')
    assert [s.string for s in styles] == ['h1{color:red}','h1{color:blue}','h1{color:green}','h1{color:black}']
    assert styles[1]['media'] == 'screen'
    assert styles[3]['media'] == 'print'


def test_nested_css_asset_keeps_stylesheet_relative_base():
    bundle=SiteBundle({'index.html':b'<link rel="stylesheet" href="css/main.css"><h1>Test</h1>',
        'css/main.css':b'h1{background:url(../img/icon.png)}','img/icon.png':b'png'},'index.html')
    assert 'data:image/png;base64,cG5n' in preview_page(bundle,'index.html')


def test_export_is_exact_revised_bundle_and_preserves_assets():
    bundle=SiteBundle({'index.html':'<html><body><h1>مرحبا</h1></body></html>'.encode(), 'logo.png':b'bytes'},'index.html')
    revised=modernize_site(bundle)
    assert site_from_zip(to_zip(revised)).files == revised.files
    assert revised.files['logo.png'] == bundle.files['logo.png']
    assert 'charset="utf-8"' in revised.files['index.html'].decode()


def test_utf8_declaration_added_without_altering_body():
    source='<html><head><title>مرحبا</title></head><body>أهلاً</body></html>'
    result=normalize_meta_utf8(source)
    assert result.count('charset="utf-8"') == 1
    assert result.split('<body>')[1] == source.split('<body>')[1]
    assert normalize_meta_utf8(result) == result


def test_import_media_condition_preserved():
    bundle=SiteBundle({'index.html':b'<link rel="stylesheet" href="main.css"><h1>Hello</h1>',
        'main.css':b'@import "print.css" print;', 'print.css':b'h1{display:none}'}, 'index.html')
    assert '@media print{h1{display:none}}' in preview_page(bundle,'index.html')


def test_bridge_preserves_existing_import_but_rejects_new_dependency():
    source='<html><body><h1>Hello</h1></body></html>'
    bundle=SiteBundle({'index.html':source.encode(),'main.css':b'@import "base.css";'},'index.html')
    changes={'index.html':source.replace('<body>','<body class="new">'),'main.css':'@import "base.css";'}
    assert apply_ai_changes(bundle,changes).files['main.css']==bundle.files['main.css']
    changes['main.css']='@import "https://unexpected.example/new.css";'
    with pytest.raises(AIIntegrationError):
        apply_ai_changes(bundle,changes)


def test_bridge_accepts_preserved_legacy_encoded_text():
    source='<html><head><meta charset="windows-1252"></head><body><h1>Café</h1></body></html>'
    bundle=SiteBundle({'index.html':source.encode('cp1252')},'index.html')
    result=apply_ai_changes(bundle,{'index.html':source.replace('<body>','<body class="new">')})
    assert 'Café' in result.files['index.html'].decode('utf-8')
    assert 'windows-1252' not in result.files['index.html'].decode('utf-8')
