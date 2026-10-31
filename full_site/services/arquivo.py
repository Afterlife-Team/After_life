"""Independent Arquivo.pt fallback, using its official CDX and raw replay API."""
import json
import re
import time
import sqlite3
from contextlib import closing
from datetime import datetime
from urllib.parse import urlsplit, urljoin, urlunsplit, parse_qsl, urlencode
import requests
from services import archive_site as archive
from services.security import validate_public_url

HOST = 'https://arquivo.pt'
CDX = HOST + '/wayback/cdx'
_blocked_until = 0.0


def _allowed(url):
    try:
        p = urlsplit(url)
        if p.scheme != 'https' or p.hostname != 'arquivo.pt' or p.port not in (None,443) or p.username or p.password:
            return False
        return p.path == '/wayback/cdx' or bool(re.match(r'^/(?:noFrame/replay|wayback)/\d{14}(?:id_)?/https?://', p.path))
    except ValueError:
        return False


def _cooldown(seconds=None):
    # Separate persistent state: Wayback's HTTP 429 must not block Arquivo.pt.
    global _blocked_until
    if seconds is not None:
        _blocked_until=max(_blocked_until,time.time()+seconds)
    db = archive._db()
    if db is None:
        return max(0,int(_blocked_until-time.time())+1)
    with closing(db):
        try:
            row=db.execute('SELECT value FROM state WHERE name=?',('arquivo_blocked_until',)).fetchone()
            if row:
                _blocked_until=max(_blocked_until,row[0])
            if seconds is not None:
                with db:
                    db.execute('INSERT OR REPLACE INTO state(name,value) VALUES (?,?)',
                               ('arquivo_blocked_until',_blocked_until))
        except sqlite3.Error:
            pass
    return max(0,int(_blocked_until-time.time())+1)


def _get(url, *, params=None, limit=archive.MAX_RESOURCE):
    if not _allowed(url):
        raise archive.ArchiveError('Blocked non-Arquivo.pt URL.')
    key=archive._request_key(url,params)
    cached=archive._cached_response(key)
    if cached is not None:
        if len(cached[0]) > limit:
            raise archive.ArchiveError('Arquivo.pt cached response exceeds allowed size.')
        return cached
    if _cooldown():
        raise archive.ArchiveRateLimited('Arquivo.pt is temporarily rate limited. Try again later.')
    current=url
    for hop in range(6):
        try:
            with requests.get(current,params=params if hop==0 else None,headers=archive.HEADERS,
                              timeout=(8,20),stream=True,allow_redirects=False) as resp:
                if resp.status_code == 429:
                    _cooldown(archive._retry_after_seconds(resp.headers.get('Retry-After')))
                    raise archive.ArchiveRateLimited('Arquivo.pt rate limit (HTTP 429). Try again later.')
                if resp.status_code in (301,302,303,307,308):
                    current=urljoin(current,resp.headers.get('Location',''))
                    if not _allowed(current):
                        raise archive.ArchiveError('Arquivo.pt redirected outside approved endpoints.')
                    continue
                resp.raise_for_status()
                chunks=[]; size=0
                for chunk in resp.iter_content(chunk_size=32768):
                    size+=len(chunk)
                    if size > limit:
                        raise archive.ArchiveError('Arquivo.pt response exceeds allowed size.')
                    chunks.append(chunk)
                raw=b''.join(chunks)
                ct=resp.headers.get('Content-Type','')
                archive._cache_success(key,raw,ct,url)
                return raw,ct
        except requests.RequestException as exc:
            raise archive.ArchiveError(f'Arquivo.pt unavailable: {exc}') from exc
    raise archive.ArchiveError('Too many Arquivo.pt redirects.')


def _without_tracking(url):
    p=urlsplit(url)
    query=urlencode([(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True)
                     if not k.lower().startswith('utm_') and k.lower() not in ('gclid','fbclid')])
    return urlunsplit((p.scheme,p.netloc,p.path,query,''))


def find_snapshot(url,year=None):
    requested=validate_public_url(url)
    lookup=_without_tracking(requested)
    params={'url':lookup,'output':'json','limit':5,'sort':'reverse','filter':'=status:200'}
    if year is not None:
        params.update({'from':str(year),'to':str(year)})
    raw,_=_get(CDX,params=params,limit=100_000)
    try:
        rows=[json.loads(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip()]
    except (ValueError,UnicodeError) as exc:
        raise archive.ArchiveError('Arquivo.pt returned an invalid index.') from exc
    for row in rows:
        if not isinstance(row,dict):
            continue
        stamp=str(row.get('timestamp','')); original=row.get('url','')
        if not re.fullmatch(r'\d{14}',stamp):
            continue
        try:
            date=datetime.strptime(stamp,'%Y%m%d%H%M%S')
            p,wanted=urlsplit(original),urlsplit(lookup)
            if (p.scheme not in ('http','https') or p.username or p.password
                    or p.hostname != wanted.hostname or p.port not in (None,80,443)
                    or (p.path or '/') != (wanted.path or '/') or p.query != wanted.query
                    or str(row.get('status')) != '200' or 'html' not in str(row.get('mime','')).lower()
                    or year is not None and date.year != int(year)):
                continue
        except (TypeError,ValueError):
            continue
        return {'provider':'Arquivo.pt','timestamp':stamp,'original_url':original,
                'requested_url':requested,'requested_year':year,
                'archive_url':f'{HOST}/wayback/{stamp}/{original}'}
    return None


def recover(snapshot):
    def fetch(stamp,url):
        return _get(f'{HOST}/noFrame/replay/{stamp}id_/{url}')
    bundle=archive.recover_archived_site(snapshot,fetch_resource=fetch,
        replay_url=lambda stamp,url:f'{HOST}/wayback/{stamp}/{url}')
    bundle.source='arquivo'
    capture=bundle.recovery['capture']
    capture['provider']='Arquivo.pt'
    capture['provenance_note']='Timestamp selected by Arquivo.pt for the main snapshot. Individual pages/assets may redirect to different capture dates.'
    bundle.warnings=[w.replace('Wayback','Arquivo.pt') for w in bundle.warnings]
    for kind in ('pages','assets'):
        for item in bundle.recovery[kind]['failed_urls']:
            item['reason']=item['reason'].replace('Wayback','Arquivo.pt')
    return bundle
