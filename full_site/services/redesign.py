"""Non-AI baseline: modify the REAL site by adding one shared stylesheet to ALL pages."""
from pathlib import PurePosixPath
import posixpath
import re
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from services.site_bundle import SiteBundle, HTML_EXT, resolve_local
from services.encoding import decode_html, normalize_meta_utf8

MODERN_CSS = r'''/* 404 Afterlife — reversible, non-AI modernization layer.
   The existing HTML, content, images and stylesheets remain intact. */
:root{--al-bg:#f4f7fb;--al-panel:#ffffff;--al-ink:#142238;--al-sub:#506078;--al-primary:#345de3;--al-radius:16px}
*,*::before,*::after{box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:var(--al-bg);color:var(--al-ink);font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;line-height:1.65;min-width:0;margin:0}
body > header,header{background:linear-gradient(115deg,#142747,#24467f);color:#fff;padding:18px max(20px,calc((100% - 1100px)/2));box-shadow:0 4px 22px #162c5425}
header h1,header h2,header h3,header p{color:#fff!important}
header h1,header h2{font-size:clamp(24px,2.7vw,34px);margin:0 0 6px;line-height:1.3}
nav{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:6px}
nav a{color:var(--al-ink)!important;background:#fff!important;text-decoration:none;padding:10px 14px;border:1px solid #64748b;border-radius:8px;min-height:44px}
header a{color:#fff}
nav a:hover{background:#e5edff!important;text-decoration:underline}
header a:hover{text-decoration:underline}
main,body > article,body > section{max-width:1100px;margin:36px auto;padding:clamp(22px,4vw,46px);background:var(--al-panel);border-radius:var(--al-radius);box-shadow:0 12px 36px #27395113}
body > div:only-child{max-width:1100px;margin-inline:auto}
h1,h2,h3,h4{line-height:1.25;letter-spacing:-.025em;overflow-wrap:anywhere}
h1{font-size:clamp(30px,4vw,52px)}h2{font-size:clamp(24px,3vw,34px)}
p,li,blockquote{overflow-wrap:anywhere}
a{color:var(--al-primary)}img,svg,video{max-width:100%;height:auto}
button,input[type=submit],input[type=button],.btn{background:var(--al-primary);color:white;border:0;border-radius:12px;padding:11px 18px;cursor:pointer}
input,textarea,select{max-width:100%;min-width:0;font:inherit;background:#fff;color:var(--al-ink);border:1px solid #64748b;border-radius:9px;padding:9px}
input::placeholder,textarea::placeholder{color:#506078;opacity:1}
button,input:not([type=checkbox]):not([type=radio]):not([type=hidden]),textarea,select{min-height:44px}
button{font:inherit}
form{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin-block:24px}
:is(a,button,input,textarea,select):focus-visible{outline:3px solid #345de3;outline-offset:3px;box-shadow:0 0 0 3px white}
button:disabled,input:disabled{opacity:.65;cursor:not-allowed}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
section+section{margin-top:22px}article,.card{border-radius:14px}
table{display:block;max-width:100%;overflow-x:auto;border-collapse:collapse}
th,td{padding:10px 14px;border:1px solid #dce3ef}
footer,body>footer{background:#142238;color:#e2eaf7;text-align:center;padding:28px 20px;margin-top:40px}
footer a{color:#bcd0ff}
header[data-afterlife-shared] h2{font-size:clamp(24px,2.7vw,34px);margin:0 0 6px;color:#fff}
header[data-afterlife-shared] nav{margin-top:6px}
main[data-afterlife-main]{min-height:260px}

/* Readable editorial layout for flat legacy documents such as CERN. */
body:not(:has(>main)){width:min(1080px,calc(100% - 32px));margin:24px auto;padding:clamp(24px,5vw,56px);background:#fff;border:1px solid #dce5ed;border-top:5px solid var(--al-primary);border-radius:18px;box-shadow:0 12px 36px #1730470a}
body:not(:has(>main))>header:not(:has(h1,h2,h3,p,nav,a,img)){display:none}
body:not(:has(>main))>h1{margin:0 0 24px;padding-bottom:24px;border-bottom:1px solid #dce5ed;color:var(--al-ink)}
body>dl{display:grid;grid-template-columns:minmax(160px,.32fr) minmax(0,1fr);column-gap:28px;margin-block:30px}
body>dl>:is(dt,dd){margin:0;padding:18px 0;border-bottom:1px solid #e1e8ed}
body>dl>dt{font-weight:650}
@media(max-width:600px){body>dl{display:block}body>dl>dt{border-bottom:0;padding-bottom:4px}body>dl>dd{padding-top:0;margin-bottom:10px}body:not(:has(>main)){width:calc(100% - 16px);margin:8px auto;padding:24px 20px}}

@media(max-width:700px){main,body>article,body>section{margin:14px 10px;padding:20px}header{padding:14px 18px}nav{gap:6px}nav a{padding:7px 10px}}
'''


# Conservative enhancement for sites that already contain a substantial,
# intricate design system. Crucially, do NOT globally restyle <nav>, <header>,
# forms, tables, or all headings; that destroys established site layout.
COMPLEX_SITE_CSS = r'''/* 404 Afterlife: conservative CSS refresh for complex sites.
   Original component/grid and language navigation styles remain in control. */
:root{--al-surface:#f4f7fb;--al-ink:#17233b;--al-accent:#315ccf}
html{scroll-behavior:smooth}
body{background:var(--al-surface)}
body > main{background:#fff;max-width:1150px;margin:28px auto 32px;
  padding:25px 26px;border-radius:18px;box-shadow:0 16px 50px rgba(31,48,82,.08)}
body > footer{max-width:1150px;margin:0 auto 32px;background:#f9fbff;
  border-radius:16px;padding:28px 22px;box-shadow:0 10px 30px rgba(31,48,82,.05)}
/* Scoped Wikipedia portal rules: use existing, archived content and structure. */
body#www-wikipedia-org .central-textlogo__image{background:none!important;color:#1a2948!important;
  display:block!important;width:auto!important;height:auto!important;
  text-indent:0!important;font-family:Georgia,'Times New Roman',serif!important;
  font-size:3.3rem!important;line-height:1.15!important;
  font-weight:700!important;letter-spacing:-.035em!important}
body#www-wikipedia-org .central-textlogo{margin-top:3rem}
body#www-wikipedia-org .central-featured-lang a:link,
body#www-wikipedia-org .central-featured-lang a:visited{color:#2563bd}
body#www-wikipedia-org .lang-list-container{background:#f7f9fe;border-radius:12px}
body#www-wikipedia-org .langlist a{color:#2756bc}
body#www-wikipedia-org .footer{padding-top:2.5rem}
@media(max-width:700px){body>main{margin:12px 9px;padding:18px 12px}
  body>footer{margin:0 9px 16px;padding:16px 10px}}
'''


def _complex_original(original: SiteBundle) -> bool:
    """Prefer protecting an existing site design over injecting generic rules."""
    max_style = 0
    for page in original.pages:
        soup = BeautifulSoup(decode_html(original.files[page]), 'html.parser')
        size = sum(len(tag.get_text()) for tag in soup.find_all('style'))
        max_style = max(max_style, size)
    external_css = sum(len(data) for name, data in original.files.items()
                       if name.lower().endswith('.css'))
    return max_style > 12_000 or external_css > 35_000


def _prefer_existing_raster_src(page: str, html: str, files: dict[str, bytes]) -> str:
    """Drop unusable responsive candidates only when the normal image src is local.

    This prevents a browser selecting an absent 2x image over an existing local
    image. Leave original image src, other markup, and remote-only images intact.
    """
    soup = BeautifulSoup(html, 'html.parser')
    changed = False
    for image in soup.find_all('img', srcset=True):
        src = image.get('src', '')
        if not resolve_local(src, page, files):
            continue
        candidates = []
        for item in image.get('srcset', '').split(','):
            item = item.strip()
            if not item:
                continue
            candidate_url = item.split()[0]
            if resolve_local(candidate_url, page, files):
                candidates.append(item)
        if candidates:
            new_value = ', '.join(candidates)
            if new_value != image['srcset']:
                image['srcset'] = new_value
                changed = True
        else:
            del image['srcset']
            changed = True
    return str(soup) if changed else html


def _unique_style_name(files: dict) -> str:
    base = 'assets/afterlife-modern.css'
    if base not in files:
        return base
    i = 2
    while f'assets/afterlife-modern-{i}.css' in files:
        i += 1
    return f'assets/afterlife-modern-{i}.css'


def _shared_shell(original: SiteBundle, page: str, text: str) -> str:
    """Add homepage-derived branding/navigation to simpler secondary pages.

    Existing page text is retained. Never fabricate a menu or link targets.
    Only pages lacking a header get this optional shared shell.
    """
    if page == original.homepage:
        return text
    homepage_soup = BeautifulSoup(decode_html(original.files[original.homepage]), 'html.parser')
    source_header = homepage_soup.find('header')
    if source_header is None:
        return text
    soup = BeautifulSoup(text, 'html.parser')
    if soup.find('header') is not None:
        return text
    body = soup.body
    if body is None:
        return text

    title_el = source_header.find(['h1', 'h2', 'h3'])
    site_name = title_el.get_text(' ', strip=True) if title_el else ''
    nav_source = source_header.find('nav')
    original_links = nav_source.find_all('a', href=True) if nav_source else []

    header = soup.new_tag('header')
    header['data-afterlife-shared'] = 'homepage'
    if site_name:
        heading = soup.new_tag('h2')
        heading.string = site_name
        header.append(heading)

    nav = soup.new_tag('nav')
    for link in original_links:
        raw = str(link.get('href', '')).strip()
        target = resolve_local(raw, original.homepage, original.files)
        if target not in original.pages:
            continue
        label = link.get_text(' ', strip=True)
        if not label:
            continue
        replacement = soup.new_tag('a', href=posixpath.relpath(target, posixpath.dirname(page) or '.'))
        suffix = urlsplit(raw)
        if suffix.query:
            replacement['href'] += '?' + suffix.query
        if suffix.fragment:
            replacement['href'] += '#' + suffix.fragment
        replacement.string = label
        nav.append(replacement)
    if nav.contents:
        header.append(nav)
    if not header.contents:
        return text

    # A simple old page may be just H1, paragraph and link without <main>.
    # Wrap the EXISTING nodes; never generate replacement text.
    if body.find('main') is None:
        simple_elements = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a', 'img', 'ul', 'ol', 'form', 'br', 'hr'}
        body_elements = [x for x in body.children if getattr(x, 'name', None)]
        if body_elements and all(x.name in simple_elements for x in body_elements):
            main = soup.new_tag('main')
            main['data-afterlife-main'] = 'original-content'
            for node in list(body.contents):
                main.append(node.extract())
            body.append(main)

    body.insert(0, header)
    return str(soup)


def _make_external_links_offline_safe(html: str) -> str:
    """Convert protocol-relative navigation links for file:// HTML viewing.

    Browsers can interpret //en.wikipedia.org/ relative to file:// as a
    *file share*, so downloaded offline websites need an explicit scheme.
    Preserve internal paths/anchors and never invent missing local pages.
    """
    if not re.search(r'<a\b[^>]*\bhref\s*=\s*[\"\']?//', html, flags=re.I):
        return html
    soup = BeautifulSoup(html, 'html.parser')
    changed = False
    for anchor in soup.find_all('a', href=True):
        raw = str(anchor['href'])
        if raw.startswith('//'):
            anchor['href'] = 'https:' + raw
            changed = True
    return str(soup) if changed else html


def modernize_site(original: SiteBundle) -> SiteBundle:
    """Preserves original assets and all page text; injects an EXTRA stylesheet."""
    files = dict(original.files)
    stylesheet = _unique_style_name(files)
    files[stylesheet] = (COMPLEX_SITE_CSS if _complex_original(original) else MODERN_CSS).encode('utf-8')
    for page in original.pages:
        text = decode_html(original.files[page])
        text = _shared_shell(original, page, text)
        text = _prefer_existing_raster_src(page, text, original.files)
        text = _make_external_links_offline_safe(text)
        relative = posixpath.relpath(stylesheet, posixpath.dirname(page) or '.')
        insertion = f'\n<link rel="stylesheet" href="{relative}" data-afterlife="baseline">\n'
        if re.search(r'</head\s*>', text, re.I):
            text = re.sub(r'</head\s*>', lambda m: insertion + m.group(0), text, count=1, flags=re.I)
        elif re.search(r'<body\b', text, re.I):
            text = re.sub(r'<body\b', lambda m: '<head>' + insertion + '</head>\n' + m.group(0),
                          text, count=1, flags=re.I)
        else:
            text = insertion + text
        if not re.search(r'<meta\s+[^>]*name\s*=\s*["\']viewport', text, re.I):
            viewport = '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            text = re.sub(r'<head\s*>', lambda m: m.group(0) + '\n' + viewport,
                          text, count=1, flags=re.I)
        files[page] = normalize_meta_utf8(text).encode('utf-8')
    return original.copy_with(files)
