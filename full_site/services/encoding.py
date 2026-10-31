"""Preserve legacy text when converting old HTML pages to UTF-8 for preview/editing."""
import re
from bs4 import UnicodeDammit

ENC_DECL = re.compile(rb'charset\s*=\s*["\']?([A-Za-z0-9_.-]+)',re.I)

def decode_html(raw: bytes) -> str:
    match = ENC_DECL.search(raw[:10000])
    if match:
        encoding = match.group(1).decode('ascii','ignore')
        try: return raw.decode(encoding)
        except (LookupError,UnicodeError): pass
    try: return raw.decode('utf-8-sig')
    except UnicodeError: pass
    found = UnicodeDammit(raw,is_html=True)
    if found.unicode_markup is not None:
        return found.unicode_markup
    return raw.decode('utf-8',errors='replace')

def normalize_meta_utf8(html: str) -> str:
    """After encoding a modified page as UTF-8, avoid a stale 1990s charset meta."""
    def replace_tag(match):
        return re.sub(r'(charset\s*=\s*["\']?)([\w.-]+)',r'\g<1>utf-8',match.group(0),flags=re.I)
    html = re.sub(r'<meta\b[^>]*>',replace_tag,html,flags=re.I)
    if not re.search(r'<meta\b[^>]*charset\s*=', html, re.I):
        declaration = '<meta charset="utf-8">'
        head = re.search(r'<head\b[^>]*>', html, re.I)
        if head:
            html = html[:head.end()] + declaration + html[head.end():]
        else:
            root = re.search(r'<html\b[^>]*>', html, re.I)
            pos = root.end() if root else 0
            html = html[:pos] + '<head>' + declaration + '</head>' + html[pos:]
    return html
