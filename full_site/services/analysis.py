"""Analyze EVERY HTML page and stylesheets, without executing website code."""
import re
from pathlib import PurePosixPath
from urllib.parse import urlsplit, unquote
from bs4 import BeautifulSoup
from services.site_bundle import SiteBundle, resolve_local
from services.encoding import decode_html

CSS_COLOR = re.compile(r'#[\da-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)', re.I)
HTML_EXT = {'.html', '.htm'}

def analyze_site(bundle: SiteBundle) -> dict:
    pages = {}
    missing = set()
    external = set()
    colors = set()
    internal_links = 0
    images = 0
    link_issues = []
    online_archive_links = 0
    parsed_pages = {p:BeautifulSoup(decode_html(bundle.files[p]),'html.parser') for p in bundle.pages}
    for path in bundle.pages:
        soup = parsed_pages[path]
        title = soup.title.get_text(' ', strip=True) if soup.title else PurePosixPath(path).name
        headings = [tag.get_text(' ', strip=True)[:250] for tag in soup.select('h1,h2,h3')]
        paragraphs = [tag.get_text(' ', strip=True)[:500] for tag in soup.select('p')]
        all_links = []
        for tag in soup.select('a[href]'):
            href = str(tag.get('href','')).strip()
            all_links.append(href)
            if tag.has_attr('data-afterlife-online-archive'):
                online_archive_links += 1
            if not href or href.lower().startswith(('mailto:', 'tel:')):
                continue
            try:
                parts=urlsplit(href)
            except ValueError:
                missing.add(f'{path} → {href}')
                link_issues.append({'page':path,'href':href,'reason':'invalid_url'})
                continue
            if parts.scheme or href.startswith('//'):
                external.add(href)
            else:
                local = path if href.startswith('#') else resolve_local(href, path, bundle.files)
                if local and PurePosixPath(local).suffix.lower() in HTML_EXT:
                    if parts.path:
                        internal_links += 1
                    fragment=unquote(parts.fragment)
                    if (fragment and fragment.lower()!='top' and not fragment.startswith(':~:text=')
                            and not parsed_pages[local].find(id=fragment)
                            and not parsed_pages[local].find('a',attrs={'name':fragment})):
                        missing.add(f'{path} → {href} (missing anchor)')
                        link_issues.append({'page':path,'href':href,'reason':'missing_anchor','target':local})
                elif not local:
                    missing.add(f'{path} → {href}')
                    link_issues.append({'page':path,'href':href,'reason':'missing_file'})
        image_tags = soup.find_all('img')
        images += len(image_tags)
        for tag in image_tags:
            value = tag.get('src','')
            if value and not resolve_local(value, path, bundle.files) and not urlsplit(value).scheme and not value.startswith('//'):
                missing.add(f'{path} → {value}')
        for link in soup.find_all('link', href=True):
            if 'stylesheet' in [x.lower() for x in (link.get('rel') or [])]:
                href = link.get('href','')
                if href and not resolve_local(href, path, bundle.files) and not urlsplit(href).scheme and not href.startswith('//'):
                    missing.add(f'{path} → {href}')
        pages[path] = {
            'title': title[:200], 'headings': headings, 'paragraphs': paragraphs,
            'links': all_links, 'images': len(image_tags),
            'has_header': bool(soup.find('header')), 'has_nav': bool(soup.find('nav')),
            'forms': len(soup.find_all('form')),
        }
        for style in soup.find_all('style'):
            colors.update(CSS_COLOR.findall(style.get_text()))
        for tag in soup.find_all(style=True):
            colors.update(CSS_COLOR.findall(tag['style']))
    for path, raw in bundle.files.items():
        if PurePosixPath(path).suffix.lower() == '.css':
            text = raw.decode('utf-8-sig', errors='replace')
            colors.update(CSS_COLOR.findall(text))
            # Inspect referenced images / fonts in CSS
            for ref in re.findall(r'url\(\s*["\']?([^"\')]+)', text, re.I):
                if not ref.startswith(('data:', '#')) and not urlsplit(ref).scheme and not ref.startswith('//'):
                    if not resolve_local(ref, path, bundle.files):
                        missing.add(f'{path} → {ref}')
    kinds = {}
    for p in bundle.files:
        ext = PurePosixPath(p).suffix.lower() or '(other)'
        kinds[ext] = kinds.get(ext, 0) + 1
    return {
        'homepage': bundle.homepage, 'page_count': len(bundle.pages),
        'total_files': len(bundle.files), 'file_types': kinds,
        'page_details': pages, 'internal_links': internal_links,
        'image_elements': images, 'colors': sorted(colors)[:50],
        'missing_references': sorted(missing)[:100],
        'link_issue_count': len(link_issues), 'link_issues':link_issues[:100],
        'online_archive_link_count': online_archive_links,
        'external_references': sorted(external)[:80],
    }
