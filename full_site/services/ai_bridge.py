"""Strict contract for Rana/Suzy's AI service. No provider/model keys in source."""
import os
import re
from collections import Counter

import requests
from bs4 import BeautifulSoup
from services.site_bundle import SiteBundle, WebsiteError
from services.encoding import decode_html, normalize_meta_utf8


class AIIntegrationError(RuntimeError):
    pass


MAX_AI_TEXT = 1_200_000


def _plain_text(raw: bytes) -> str:
    soup = BeautifulSoup(decode_html(raw), 'html.parser')
    for tag in soup(['head', 'script', 'style', 'noscript']):
        tag.decompose()
    return re.sub(r'\s+', ' ', soup.get_text(' ', strip=True)).strip()


def request_ai_redesign(original: SiteBundle, endpoint: str | None = None, token: str | None = None) -> SiteBundle:
    """Send original HTML/CSS (all pages) to a trusted team endpoint; validate edits.

    Expected response: {"files": {"index.html":"...", "css/style.css":"..."}}.
    Every original HTML page must be returned; unchanged non-HTML assets are preserved.
    """
    endpoint = (endpoint or os.environ.get('AFTERLIFE_AI_ENDPOINT','')).strip()
    token = token or os.environ.get('AFTERLIFE_AI_API_KEY','')
    if not endpoint:
        raise AIIntegrationError('AI endpoint is not configured. Use CSS baseline until the team connects its model.')
    from urllib.parse import urlsplit
    url = urlsplit(endpoint)
    if url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ('localhost','127.0.0.1')):
        raise AIIntegrationError('AI endpoint must be HTTPS or local HTTP.')
    editable = {p: decode_html(v) for p,v in original.files.items()
                if p.lower().endswith(('.html', '.htm', '.css'))}
    if sum(len(t.encode('utf-8')) for t in editable.values()) > MAX_AI_TEXT:
        raise AIIntegrationError('AI input too large (HTML/CSS > 1.2 MB). Try a smaller website.')
    payload = {'task': 'modernize_existing_website', 'homepage': original.homepage,
               'files': editable,
               'assets': sorted(p for p in original.files if p not in editable),
               'rules': ['Preserve all original text, links, image references and page count',
                         'Return HTML/CSS edits for the existing paths only',
                         'Do not include JavaScript, forms that send data, or external resources',
                         'Use one consistent responsive design across all HTML pages']}
    headers = {'Content-Type':'application/json'}
    if token: headers['Authorization'] = f'Bearer {token}'
    try:
        r = requests.post(endpoint, json=payload, headers=headers, timeout=(5,120), allow_redirects=False)
        r.raise_for_status()
        if len(r.content) > 3_000_000:
            raise AIIntegrationError('AI response exceeded 3 MB.')
        data = r.json()
    except (requests.RequestException, ValueError) as exc:
        raise AIIntegrationError(f'AI endpoint error: {exc}') from exc
    changes = data.get('files') if isinstance(data,dict) else None
    if not isinstance(changes,dict) or not changes:
        raise AIIntegrationError('AI response must contain a nonempty "files" object.')
    return apply_ai_changes(original, changes)


def apply_ai_changes(original: SiteBundle, changes: dict) -> SiteBundle:
    """Validate response from team endpoint OR manually imported AI JSON."""
    if not isinstance(changes,dict) or not changes:
        raise AIIntegrationError('No AI file edits supplied.')
    editable = {p for p in original.files if p.lower().endswith(('.html','.htm','.css'))}
    missing_pages = set(original.pages) - set(changes)
    if missing_pages:
        raise AIIntegrationError('AI must return the redesigned HTML for every page. Missing: ' + ', '.join(sorted(missing_pages)[:10]))
    new_files = dict(original.files)
    for path, updated in changes.items():
        if path not in editable or not isinstance(updated,str):
            raise AIIntegrationError(f'AI attempted to edit an unsupported file: {path}')
        if len(updated.encode('utf-8')) > 1_500_000:
            raise AIIntegrationError(f'AI result too large: {path}')
        if path.lower().endswith(('.html','.htm')):
            before_html = BeautifulSoup(decode_html(original.files[path]),'html.parser')
            after_html = BeautifulSoup(updated,'html.parser')
            before = _plain_text(original.files[path]); after = _plain_text(updated.encode('utf-8'))
            if before and not _content_preserved(before, after):
                raise AIIntegrationError(f'AI removed or changed visible text in {path}. Rejected.')
            for selector, attribute in [('a[href]','href'),('img[src]','src')]:
                old_refs = {t.get(attribute) for t in before_html.select(selector)}
                new_refs = {t.get(attribute) for t in after_html.select(selector)}
                if not old_refs.issubset(new_refs):
                    raise AIIntegrationError(f'AI dropped original links/images in {path}. Rejected.')
            old_scripts = [str(t) for t in before_html.find_all('script')]
            new_scripts = [str(t) for t in after_html.find_all('script')]
            if new_scripts != old_scripts:
                raise AIIntegrationError('AI cannot insert or alter JavaScript script tags.')
            old_handlers = sorted((t.name,k,v) for t in before_html.find_all(True) for k,v in t.attrs.items() if k.lower().startswith('on'))
            new_handlers = sorted((t.name,k,v) for t in after_html.find_all(True) for k,v in t.attrs.items() if k.lower().startswith('on'))
            if new_handlers != old_handlers:
                raise AIIntegrationError('AI cannot insert or alter inline event handlers.')
        elif re.search(r'@import\b|url\(\s*["\']?https?://',updated,re.I):
            raise AIIntegrationError('AI may not introduce remote CSS dependencies.')
        new_files[path] = (normalize_meta_utf8(updated) if path.lower().endswith(('.html','.htm')) else updated).encode('utf-8')
    if all(new_files[p] == original.files[p] for p in changes):
        raise AIIntegrationError('AI returned identical files; no redesign changes were made.')
    return original.copy_with(new_files)




def _content_preserved(before: str, after: str) -> bool:
    """
    Check preservation of original visible text.

    Allows:
    - Added headers and navigation text
    - Sentence reordering
    - Whitespace and case differences

    Rejects:
    - Missing original sentence segments
    - Missing repeated sentences
    - Sentences changed into longer, different sentences

    Conservative textual validation, not a semantic guarantee.
    """

    def normalize(text: str) -> str:
        return re.sub(r'\s+', ' ', text).casefold().strip()

    original = normalize(before)
    redesigned = normalize(after)

    if not original:
        return True

    # First, accept if the entire original text is still present.
    if original in redesigned:
        return True

    # Keep sentence-ending punctuation as part of each segment.
    segments = [
        part.strip()
        for part in re.findall(r'[^.!?؟]+[.!?؟]*', original)
        if part.strip()
    ]

    for segment, required_count in Counter(segments).items():
        # Match at a word boundary so added headers are allowed,
        # but different words or altered sentences are not.
        pattern = r'(?<!\w)' + re.escape(segment) + r'(?!\w)'

        actual_count = len(re.findall(pattern, redesigned))

        if actual_count < required_count:
            return False

    return True
