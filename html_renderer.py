from html import escape
from pathlib import PurePosixPath
from urllib.parse import urlsplit, unquote
import re

THEMES = {
    'ocean': {'hero': '#12375b', 'bg': '#edf5fc', 'ink': '#162c42', 'accent': '#1774b8', 'soft': '#deeffb'},
    'forest': {'hero': '#18483c', 'bg': '#eff7f1', 'ink': '#173b32', 'accent': '#26795a', 'soft': '#dff0e5'},
    'sunset': {'hero': '#68304d', 'bg': '#fff5f0', 'ink': '#42263a', 'accent': '#bc5272', 'soft': '#ffe4dc'},
}
LAYOUTS = {'cards', 'minimal', 'editorial'}


def safe_local_href(href):
    """Allow simple relative HTML links only; no scripts, network URLs or traversal."""
    if not isinstance(href, str):
        return None
    href = href.strip()
    if not href or len(href) > 300 or '\\' in href or any(ord(c) < 32 for c in href):
        return None
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or href.startswith(('/', '#')) or parsed.query or parsed.fragment:
        return None
    decoded = unquote(parsed.path)
    if '%' in decoded or not re.fullmatch(r'[A-Za-z0-9_./-]+', decoded):
        return None
    if not decoded.lower().endswith(('.html', '.htm')):
        return None
    if any(part in ('.', '..') for part in decoded.split('/')):
        return None
    return href


def render_navigation(navigation):
    items = []
    for link in navigation if isinstance(navigation, list) else []:
        if not isinstance(link, dict):
            continue
        label = escape(str(link.get('label') or '').strip())
        status = link.get('status')
        href = safe_local_href(link.get('href'))
        if not label:
            continue
        if status == 'missing':
            items.append(f'<span class="nav-missing">{label} - Missing Page</span>')
        elif status == 'working' and href:
            # Works in a ZIP export where paths and directory structure are preserved.
            items.append(f'<a class="nav-item" href="{escape(href, quote=True)}">{label}</a>')
        else:
            items.append(f'<span class="nav-item">{label}</span>')
    return '<nav aria-label="Original website navigation">' + ''.join(items) + '</nav>' if items else ''


def render_website(data):
    title = escape(str(data.get('title') or 'Restored Website'))
    subtitle = escape(str(data.get('subtitle') or ''))
    theme = data.get('theme', 'ocean')
    layout = data.get('layout', 'cards')
    theme = theme if theme in THEMES else 'ocean'
    layout = layout if layout in LAYOUTS else 'cards'
    colors = THEMES[theme]
    sections_html = []
    for section in data.get('sections', []):
        if not isinstance(section, dict):
            continue
        heading = escape(str(section.get('heading') or ''))
        text = escape(str(section.get('text') or ''))
        if not heading and not text:
            continue
        heading_html = f'<h2>{heading}</h2>' if heading else ''
        paragraph_html = f'<p>{text}</p>' if text else ''
        sections_html.append(f'<section class="card">{heading_html}{paragraph_html}</section>')
    cards = '\n'.join(sections_html)
    subtitle_html = f'<p>{subtitle}</p>' if subtitle else ''
    nav = render_navigation(data.get('navigation', []))
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: Arial, sans-serif; background: {colors['bg']}; color: {colors['ink']}; line-height: 1.65; }}
header {{ padding: 70px 24px; text-align: center; background: {colors['hero']}; color: white; }}
header h1 {{ font-size: clamp(2rem, 5vw, 3.5rem); margin: 0; }}
header p {{ font-size: 1.1rem; }}
nav {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 12px; padding: 20px; background: white; }}
.nav-item, .nav-missing {{ display: inline-block; border-radius: 10px; padding: 10px 16px; font-weight: bold; text-decoration: none; }}
.nav-item {{ color: {colors['hero']}; background: {colors['soft']}; }}
.nav-missing {{ color: #9f1239; background: #fff1f2; border: 1px solid #fecdd3; }}
main {{ max-width: 1080px; margin: 35px auto; padding: 0 22px; }}
.card {{ padding: 25px; margin-bottom: 20px; background: white; border-radius: 16px; border-top: 4px solid {colors['accent']}; box-shadow: 0 7px 24px #00000012; }}
.card h2 {{ margin-top: 0; color: {colors['hero']}; }}
body.layout-minimal .card {{ box-shadow: none; border-radius: 0; border: 0; border-bottom: 1px solid {colors['accent']}; }}
body.layout-editorial main {{ max-width: 850px; }}
body.layout-editorial .card {{ border: 0; border-left: 6px solid {colors['accent']}; box-shadow: none; border-radius: 0; }}
@media (max-width: 600px) {{ header {{ padding: 42px 16px; }} main {{ margin: 20px auto; }} }}
</style>
</head>
<body class="layout-{layout}">
<header><h1>{title}</h1>{subtitle_html}</header>
{nav}
<main>
{cards}
</main>
</body>
</html>'''
