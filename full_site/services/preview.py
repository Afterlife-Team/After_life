"""Restricted *static* HTML preview for a single page of a real website bundle.

Never fetch external assets or execute source JavaScript. The Streamlit iframe is
an additional isolation layer. Use a separate origin + CSP HTTP headers for
production deployments; HTML meta CSP alone isn't a full security boundary.
"""
import base64
import mimetypes
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, unquote_to_bytes
from bs4 import BeautifulSoup
from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException
from services.site_bundle import SiteBundle, resolve_local, WebsiteError
from services.encoding import decode_html, normalize_meta_utf8

IMG_EXT = {'.png','.jpg','.jpeg','.gif','.webp','.ico','.bmp','.svg'}
FONT_EXT = {'.woff','.woff2','.ttf','.otf','.eot'}
CSS_URL = re.compile(r'url\(\s*(["\']?)(.*?)\1\s*\)', re.I|re.S)
CSS_IMPORT = re.compile(r'@import\s+(?:url\([^)]*\)|["\'][^"\']*["\'])[^;]*;?', re.I)
DISALLOWED = {'script','iframe','frame','frameset','object','embed','applet','base',
              'template','portal','canvas','video','audio','source','track'}
SVG_TAGS = {'svg','g','path','rect','circle','ellipse','line','polyline','polygon',
            'text','tspan','defs','linearGradient','radialGradient','stop',
            'clipPath','mask','use','pattern','title','desc','symbol'}
SVG_ATTRS = {'xmlns','width','height','viewBox','fill','stroke','stroke-width',
             'stroke-linecap','stroke-linejoin','stroke-dasharray','d','points',
             'transform','x','y','x1','x2','y1','y2','cx','cy','r','rx','ry',
             'opacity','fill-opacity','stroke-opacity','offset','stop-color',
             'stop-opacity','id','class','font-size','font-family','font-weight',
             'text-anchor','preserveAspectRatio','gradientUnits','gradientTransform',
             'spreadMethod','clip-path','mask','xmlns:xlink'}

def _clean_svg(source: bytes) -> bytes | None:
    """Whitelist static SVG nodes/attributes. No scripts, foreignObject or URLs."""
    try:
        root = SafeET.fromstring(source)
        def cleanse(node):
            tag = node.tag.split('}')[-1] if isinstance(node.tag,str) else ''
            if tag not in SVG_TAGS:
                return False
            for attr, val in list(node.attrib.items()):
                key = attr.split('}')[-1]
                if key == 'href':
                    if not val.startswith('#'):
                        del node.attrib[attr]
                elif key not in SVG_ATTRS or 'url(' in val.lower() or 'javascript:' in val.lower():
                    del node.attrib[attr]
            for child in list(node):
                if not cleanse(child): node.remove(child)
            return True
        if not cleanse(root): return None
        return ET.tostring(root, encoding='utf-8')
    except (ValueError, SafeET.ParseError, ET.ParseError, DefusedXmlException):
        return None


def _asset_data(raw: str, current: str, bundle: SiteBundle, *, font=False) -> str | None:
    if raw.startswith('data:'):
        # Preserve safe, small inline raster images/fonts already in old pages.
        match = re.match(r'^data:([\w.+/-]+);base64,([A-Za-z0-9+/=\s]+)$',raw,re.I)
        if match:
            mime = match.group(1).lower()
            allowed_mime = ({'font/woff','font/woff2','application/font-woff','application/x-font-ttf','font/ttf'}
                            if font else {'image/png','image/jpeg','image/gif','image/webp','image/bmp'})
            if mime in allowed_mime and len(match.group(2)) < 1_500_000:
                try:
                    data = base64.b64decode(match.group(2),validate=True)
                    if len(data) < 1_000_000: return raw
                except (ValueError,base64.binascii.Error):
                    pass
        return None
    path = resolve_local(raw, current, bundle.files)
    if path is None: return None
    ext = '.' + path.rsplit('.',1)[-1].lower() if '.' in path else ''
    if ext not in (FONT_EXT if font else IMG_EXT): return None
    data = bundle.files[path]
    if ext == '.svg':
        data = _clean_svg(data)
        if data is None: return None
        mime = 'image/svg+xml'
    else:
        mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    return 'data:' + mime + ';base64,' + base64.b64encode(data).decode('ascii')


def _clean_css(css: str, path: str, bundle: SiteBundle, visited=None) -> str:
    """Inline locally referenced @import and binary assets; block external requests."""
    visited = visited or set()
    if path in visited: return ''
    visited = visited | {path}
    # Remove comments first to avoid importing URLs concealed by comments.
    css = re.sub(r'/\*.*?\*/','',css,flags=re.S)
    def replace_import(match):
        item = match.group(0)
        ref = re.search(r'@import\s+(?:url\(\s*["\']?([^"\')]+)|["\']([^"\']+))', item, re.I)
        raw = (ref.group(1) or ref.group(2)) if ref else ''
        local = resolve_local(raw, path, bundle.files)
        if local and local.lower().endswith('.css') and local not in visited:
            imported = _clean_css(decode_html(bundle.files[local]),local,bundle,visited)
            # Preserve an import's media condition instead of applying print CSS
            # to every preview. Unsupported modern clauses stay blocked.
            suffix = re.sub(r'^@import\s+(?:url\([^)]*\)|["\'][^"\']*["\'])', '', item, flags=re.I).strip().rstrip(';').strip()
            if suffix:
                if suffix.lower().startswith(('layer', 'supports')):
                    return ''
                return '@media ' + suffix + '{' + imported + '}'
            return imported
        return ''
    css = CSS_IMPORT.sub(replace_import,css)
    css = re.sub(r'@charset\s+[^;]+;','',css, flags=re.I)
    css = re.sub(r'expression\s*\(', 'disabled(', css, flags=re.I)
    css = re.sub(r'-moz-binding\s*:', 'disabled:', css, flags=re.I)
    def replace_url(match):
        value = match.group(2).strip()
        data = _asset_data(value,path,bundle,font=True) or _asset_data(value,path,bundle)
        return f'url("{data}")' if data else 'url("")'
    return CSS_URL.sub(replace_url,css)


def preview_page(bundle: SiteBundle, page: str, *, internal_navigation=False) -> str:
    if page not in bundle.pages:
        raise WebsiteError('Selected preview page does not exist.')
    soup = BeautifulSoup(decode_html(bundle.files[page]),'html.parser')
    if not soup.html:
        root = soup.new_tag('html')
        body = soup.new_tag('body')
        for node in list(soup.contents): body.append(node.extract())
        root.append(body); soup.append(root)
    if not soup.head:
        soup.html.insert(0,soup.new_tag('head'))
    original_stylesheets = []
    # Replace each link IN PLACE: moving linked CSS after inline overrides changes
    # the cascade and makes preview disagree with the exported website.
    for tag in list(soup.find_all('link',href=True)):
        if 'stylesheet' in [r.lower() for r in (tag.get('rel') or [])] and not tag.has_attr('disabled'):
            p = resolve_local(tag['href'],page,bundle.files)
            if p and p.lower().endswith('.css'):
                original_stylesheets.append(p)
                replacement = soup.new_tag('style')
                replacement['data-original-css'] = p
                if tag.get('media'):
                    replacement['media'] = tag['media']
                replacement.string = _clean_css(decode_html(bundle.files[p]),p,bundle)
                tag.replace_with(replacement)
    # Iterate fresh lists after removals to avoid decompose() NoneType bug.
    for tag in list(soup.find_all(True)):
        if tag.name is not None and tag.name.lower() in DISALLOWED:
            tag.decompose()
    for tag in list(soup.find_all(['link'])):
        if tag.name is not None: tag.decompose()
    for tag in list(soup.find_all('meta')):
        if tag.name and (tag.get('http-equiv','').lower() in ('refresh','content-security-policy')):
            tag.decompose()
    for svg in list(soup.find_all('svg')):
        if svg.name is not None: svg.decompose()
    for tag in soup.find_all(True):
        if not tag.attrs: continue
        tag.attrs.pop('data-afterlife-page',None)
        tag.attrs.pop('data-afterlife-fragment',None)
        for attr in list(tag.attrs):
            if attr not in tag.attrs: continue
            name = attr.lower()
            if name.startswith('on') or name in {'srcdoc','integrity','nonce','ping','formaction','target','download'}:
                del tag.attrs[attr]
            elif name == 'style':
                tag[attr] = _clean_css(str(tag[attr]),page,bundle)
            elif name == 'src':
                data = _asset_data(str(tag[attr]),page,bundle) if tag.name == 'img' else None
                if data: tag[attr] = data
                else: del tag.attrs[attr]
            elif name in {'href','xlink:href'}:
                # Links to real external sites may open in a separate browser tab.
                # Internal pages remain controlled by the Streamlit page selector:
                # no arbitrary iframe navigation or execution of uploaded scripts.
                raw_href = str(tag[attr]).strip()
                candidate = ('https:' + raw_href) if raw_href.startswith('//') else raw_href
                try:
                    parsed_link = urlsplit(candidate)
                    allow_external = (tag.name == 'a' and name == 'href'
                        and parsed_link.scheme.lower() in ('https', 'http')
                        and parsed_link.hostname is not None
                        and parsed_link.username is None
                        and parsed_link.password is None
                        and parsed_link.port in (None, 80, 443))
                except ValueError:
                    allow_external = False
                if allow_external:
                    tag[attr] = candidate
                elif (internal_navigation and tag.name=='a' and name=='href'
                      and resolve_local(raw_href,page,bundle.files) in bundle.pages):
                    tag[attr]='#'
                    tag['data-afterlife-page']=resolve_local(raw_href,page,bundle.files)
                    tag['data-afterlife-fragment']=urlsplit(raw_href).fragment
                elif tag.name == 'a' and name == 'href' and raw_href.startswith('#'):
                    tag[attr] = raw_href  # Same-page section anchors only.
                else:
                    del tag.attrs[attr]
                    if tag.name == 'a' and name == 'href':
                        tag['title'] = 'For internal pages, use the page selector above.'
            elif name in {'srcset','poster','data','action','formaction','cite','background'}:
                del tag.attrs[attr]
        if tag.name in {'input','button','select','textarea','option','fieldset'}:
            tag['disabled'] = 'disabled'
        if tag.name == 'form':
            tag.attrs.pop('action',None); tag.attrs.pop('method',None)
    # Setting these attributes after the cleanup avoids restoring attacker-supplied
    # targets. Popup navigation is user-initiated; scripts and remote resources
    # inside the preview remain blocked by the CSP.
    for anchor in soup.find_all('a', href=True):
        href = str(anchor['href'])
        if href.startswith(('https://', 'http://')):
            anchor['target'] = '_blank'
            anchor['rel'] = 'noopener noreferrer'
            anchor['referrerpolicy'] = 'no-referrer'

    # Inlined <style> blocks: external refs and imports eliminated.
    for tag in soup.find_all('style'):
        if tag.has_attr('data-original-css'):
            continue
        tag.string = _clean_css(tag.get_text(),page,bundle)
    # The archived Wikipedia wordmark is normally a sprite background. If the
    # sprite wasn't recoverable, reveal its ORIGINAL "Wikipedia" text instead.
    # This also repairs the BEFORE preview; source ZIP remains unchanged.
    if soup.select_one('.central-textlogo__image') and not any(
            name.lower().endswith('.svg') for name in bundle.files):
        fallback = soup.new_tag('style')
        fallback['data-afterlife-missing-sprite-fallback'] = 'true'
        fallback.string = (
            '.central-textlogo__image{background:none!important;'
            'color:#1a2948!important;display:block!important;'
            'width:auto!important;height:auto!important;'
            'text-indent:0!important;font:bold 3rem/1.15 Georgia,serif!important}'
        )
        soup.head.append(fallback)
    # Very old plain HTML can have no CSS at all. Give the PREVIEW a readable
    # white page rather than inheriting Streamlit's dark iframe background.
    # This is preview-only and does not modify the source/downloaded ZIP.
    if not original_stylesheets and not soup.find('style'):
        defaults = soup.new_tag('style')
        defaults['data-afterlife-preview-default'] = 'true'
        defaults.string = 'html,body{background:#fff;color:#141414;}'
        soup.head.insert(0, defaults)
    meta = soup.new_tag('meta')
    meta['http-equiv'] = 'Content-Security-Policy'
    meta['content'] = ("default-src 'none'; script-src 'none'; connect-src 'none'; "
                       "img-src data:; font-src data:; style-src 'unsafe-inline'; "
                       "base-uri 'none'; form-action 'none'; object-src 'none'")
    soup.head.insert(0,meta)
    return '<!doctype html>\n' + normalize_meta_utf8(str(soup))
