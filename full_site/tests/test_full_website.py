import io
import json
import zipfile
import pytest
from services.site_bundle import site_from_zip, to_zip, resolve_local, WebsiteError
from services.analysis import analyze_site
from services.preview import preview_page
from services.redesign import modernize_site
from services.ai_bridge import apply_ai_changes, AIIntegrationError, _content_preserved, _plain_text


def make_site(files):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        for path, contents in files.items():
            info = zipfile.ZipInfo(path)
            info.filename = path  # Keep raw Windows separators for the rejection test.
            z.writestr(info,contents)
    return site_from_zip(stream.getvalue())


def fixture_site():
    return make_site({
        'index.html': '''<!doctype html><html><head><title>Real Old Store</title><link rel="stylesheet" href="css/main.css"></head><body><header><h1>Real Old Store</h1><nav><a href="about.html">About</a><a href="pages/contact.html">Contact</a></nav></header><main><p>Welcome to our authentic older website and products.</p><img src="images/logo.svg" alt="Logo"><form action="https://evil.example"><input placeholder="email"><button>Send</button></form><script>window.alert('BAD');</script></main></body></html>''',
        'about.html': '<html><head><title>About Us</title></head><body><h1>About Us</h1><p>We are an independent technology store founded years ago.</p></body></html>',
        'pages/contact.html': '<html><body><h1>Contact our team</h1><p>Reach out using our customer support details.</p><a href="../index.html">Home</a></body></html>',
        'css/main.css':'body {background:#f1e0aa} header {color:#345} .logo {background: url("../images/pic.png")}',
        'images/logo.svg':'<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50"><script>alert(1)</script><circle cx="25" cy="25" r="20" fill="red"/></svg>',
        'images/pic.png':b'\x89PNG\r\n\x1a\n',
        'js/old.js': 'alert("original script retained but not executed in previews")',
    })


def test_reads_all_pages_and_keeps_files():
    s=fixture_site()
    assert len(s.pages)==3
    assert len(s.files)==7
    assert s.homepage=='index.html'
    with zipfile.ZipFile(io.BytesIO(to_zip(s))) as z:
        assert sorted(z.namelist()) == sorted(s.files)
        assert z.read('js/old.js') == s.files['js/old.js']


def test_analysis_all_pages_and_css_colors():
    rep=analyze_site(fixture_site())
    assert rep['page_count']==3
    assert '#f1e0aa' in rep['colors']
    assert not rep['missing_references']
    assert rep['internal_links']==3


def test_redesign_all_pages_preserves_original_text_and_assets():
    s=fixture_site(); r=modernize_site(s)
    assert set(s.pages)==set(r.pages)
    assert len(r.files)==len(s.files)+1
    assert r.files['images/logo.svg']==s.files['images/logo.svg']
    assert r.files['js/old.js']==s.files['js/old.js']
    for p in s.pages:
        assert b'data-afterlife="baseline"' in r.files[p]
        assert _content_preserved(_plain_text(s.files[p]), _plain_text(r.files[p]))
    assert b'../assets/afterlife-modern.css' in r.files['pages/contact.html']


def test_preview_css_svg_script_forms_and_links():
    s=fixture_site(); html=preview_page(s,'index.html')
    assert '#f1e0aa' in html
    assert 'data:image/svg+xml;base64,' in html
    assert '<script' not in html
    assert 'window.alert' not in html
    assert 'action="https://evil.example"' not in html
    assert ' disabled=' in html
    assert 'href="about.html"' not in html
    assert 'script-src \'none\'' in html
    assert 'alert(1)' not in html


def test_preview_does_not_mutate_original():
    s=fixture_site()
    before=dict(s.files)
    preview_page(s,'index.html')
    assert s.files==before


def test_reject_path_traversal_symlink_duplicate_and_size():
    for bad in ('../evil.html','C:/evil.html','/absolute.html','dir/../../escape.html','dir\\win.html'):
        with pytest.raises(WebsiteError):
            make_site({'index.html':'<h1>Okay</h1>',bad:'bad'})
    with pytest.raises(WebsiteError):
        make_site({'index.html':'<h1>Okay</h1>','INDEX.HTML':'<h1>Duplicate</h1>'})
    with pytest.raises(WebsiteError):
        make_site({'file.txt':'no html'})


def test_reject_symlink():
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        z.writestr('index.html','<html></html>')
        info=zipfile.ZipInfo('unsafe.png');info.create_system=3
        info.external_attr=(0o120777 << 16)
        z.writestr(info,'/etc/passwd')
    with pytest.raises(WebsiteError):
        site_from_zip(stream.getvalue())


def test_resolve_nested_and_root_paths():
    files={'index.html':b'', 'images/a.png':b'', 'pages/contact.html':b''}
    assert resolve_local('../images/a.png','pages/contact.html',files)=='images/a.png'
    assert resolve_local('/images/a.png','pages/contact.html',files)=='images/a.png'
    assert resolve_local('../../../etc/passwd','pages/contact.html',files) is None
    assert resolve_local('https://evil.com/logo.png','index.html',files) is None


def test_ai_rejects_missing_content_and_untrusted_file_paths():
    s=fixture_site()
    with pytest.raises(AIIntegrationError):
        apply_ai_changes(s,{'index.html':'<html><body>Completely different store</body></html>'})
    with pytest.raises(AIIntegrationError):
        apply_ai_changes(s,{'js/old.js':'alert(2)'})
    with pytest.raises(AIIntegrationError):
        apply_ai_changes(s,{'new.html':'<html></html>'})


def test_ai_accepts_same_site_html_css_edits():
    s=fixture_site()
    html=s.files['about.html'].decode().replace('<body>','<body class="refreshed">')
    changed=apply_ai_changes(s,{'index.html':s.files['index.html'].decode(), 'pages/contact.html':s.files['pages/contact.html'].decode(), 'about.html':html,'css/main.css':'body{background:#ffffff}'})
    assert changed.files['about.html']==html.encode()
    assert changed.files['index.html']==s.files['index.html']
    assert changed.files['images/logo.svg']==s.files['images/logo.svg']


def test_ai_blocks_dropped_images_and_new_scripts():
    s=fixture_site(); original=s.files['index.html'].decode()
    base={p: s.files[p].decode() for p in s.pages}
    with pytest.raises(AIIntegrationError):
        apply_ai_changes(s,{**base,'index.html':original.replace('<img src="images/logo.svg" alt="Logo">','')})
    with pytest.raises(AIIntegrationError):
        apply_ai_changes(s,{**base,'index.html':original+'<script src="https://evil.example/x.js"></script>'})
    with pytest.raises(AIIntegrationError):
        apply_ai_changes(s,{'about.html':s.files['about.html'].decode()})


def test_legacy_latin1_html_characters_survive_redesign():
    old='<html><head><meta charset="windows-1252"></head><body><h1>Café résumé</h1></body></html>'
    s=make_site({'index.html':old.encode('windows-1252')})
    r=modernize_site(s)
    assert 'Café résumé' in r.files['index.html'].decode('utf-8')
    assert 'charset="utf-8"' in r.files['index.html'].decode('utf-8')
    assert 'Café résumé' in preview_page(s,'index.html')


def test_safe_inline_data_png_is_preserved():
    s=make_site({'index.html':'<html><body><img src="data:image/png;base64,iVBORw0KGgo="></body></html>'})
    preview=preview_page(s,'index.html')
    assert 'data:image/png;base64,iVBORw0KGgo=' in preview


def test_css_external_resources_are_not_loaded_in_preview():
    s=make_site({'index.html':'<html><head><link rel="stylesheet" href="css/a.css"></head><body><h1>Hello</h1></body></html>',
                 'css/a.css':'@import "https://evil.example/z.css";body{background:url(https://evil.example/track.png);color:#abc}'})
    preview=preview_page(s,'index.html')
    assert 'https://evil.example' not in preview
    assert '#abc' in preview


def test_ai_rejects_changed_short_text():
    original = make_site({'index.html': '<html><body><h1>Our shop</h1></body></html>'})
    with pytest.raises(AIIntegrationError, match='visible text'):
        apply_ai_changes(original, {'index.html': '<html><body><h1>New shop</h1></body></html>'})


def test_preview_rejects_svg_entities_without_crashing():
    original = make_site({
        'index.html': '<html><body><img src="logo.svg"></body></html>',
        'logo.svg': '<!DOCTYPE svg [<!ENTITY x "unsafe">]><svg xmlns="http://www.w3.org/2000/svg"><text>&x;</text></svg>',
    })
    assert 'data:image/svg+xml' not in preview_page(original, 'index.html')
