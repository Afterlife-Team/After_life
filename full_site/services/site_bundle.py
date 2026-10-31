"""Validated, in-memory website files. No uploaded file is executed."""
from dataclasses import dataclass, field
from pathlib import PurePosixPath
import io
import posixpath
import stat
import zipfile

MAX_UPLOAD = 15 * 1024 * 1024
MAX_TOTAL = 45 * 1024 * 1024
MAX_EACH = 7 * 1024 * 1024
MAX_FILES = 350
ALLOWED = {'.html', '.htm', '.css', '.js', '.mjs', '.json', '.png', '.jpg',
           '.jpeg', '.gif', '.webp', '.svg', '.ico', '.bmp', '.woff', '.woff2',
           '.ttf', '.otf', '.eot', '.txt', '.xml', '.webmanifest', '.pdf'}
HTML_EXT = {'.html', '.htm'}

class WebsiteError(ValueError):
    """Invalid website ZIP / path / resource."""

@dataclass
class SiteBundle:
    files: dict[str, bytes]
    homepage: str
    source: str = 'zip'
    source_url: str = ''
    warnings: list[str] = field(default_factory=list)
    recovery: dict = field(default_factory=dict)  # Provenance and crawl coverage for Wayback imports.

    @property
    def pages(self) -> list[str]:
        return sorted(p for p in self.files if PurePosixPath(p).suffix.lower() in HTML_EXT)

    def copy_with(self, files: dict[str, bytes]) -> 'SiteBundle':
        return SiteBundle(files, self.homepage, self.source, self.source_url, list(self.warnings), dict(self.recovery))


def safe_path(path: str) -> str:
    if not path or not isinstance(path, str) or '\\' in path or path.startswith('/') or '\x00' in path:
        raise WebsiteError('Unsafe ZIP path.')
    parts = path.split('/')
    if any(part in ('.', '..') or ':' in part or not part for part in parts):
        raise WebsiteError(f'Unsafe ZIP path: {path!r}')
    if len(parts) > 20 or len(path) > 220:
        raise WebsiteError('File path too long / nested.')
    return '/'.join(parts)


def site_from_zip(data: bytes) -> SiteBundle:
    if not data or len(data) > MAX_UPLOAD:
        raise WebsiteError('ZIP must be smaller than 15 MB.')
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError) as exc:
        raise WebsiteError('Not a valid ZIP archive.') from exc
    files = {}
    total = 0
    seen = set()
    skipped = []
    with archive:
        entries = archive.infolist()
        if len(entries) > MAX_FILES:
            raise WebsiteError('ZIP contains too many entries (maximum 350).')
        for info in entries:
            if info.is_dir():
                continue
            path = safe_path(info.orig_filename)
            if info.flag_bits & 0x1:
                raise WebsiteError('Encrypted ZIP files are not supported.')
            if info.create_system == 3:
                mode = info.external_attr >> 16
                if stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                    raise WebsiteError('ZIP contains a symlink or special file.')
            if path.casefold() in seen:
                raise WebsiteError('Duplicate filenames in ZIP.')
            seen.add(path.casefold())
            if PurePosixPath(path).suffix.lower() not in ALLOWED:
                skipped.append(path)
                continue
            if info.file_size > MAX_EACH:
                raise WebsiteError('ZIP contains a file exceeding 7 MB.')
            total += info.file_size
            if total > MAX_TOTAL:
                raise WebsiteError('Uncompressed ZIP exceeds 45 MB.')
            try:
                with archive.open(info) as handle:
                    raw = handle.read(MAX_EACH + 1)
            except (OSError, RuntimeError, zipfile.BadZipFile, EOFError) as exc:
                raise WebsiteError(f'Could not read {path}.') from exc
            if len(raw) > MAX_EACH:
                raise WebsiteError('Unexpected oversized ZIP entry.')
            files[path] = raw
    pages = sorted(path for path in files if PurePosixPath(path).suffix.lower() in HTML_EXT)
    if not pages:
        raise WebsiteError('ZIP must contain at least one .html or .htm file.')
    indices = [p for p in pages if PurePosixPath(p).name.lower() in ('index.html', 'index.htm')]
    homepage = min(indices or pages, key=lambda p: (p.count('/'), p.lower()))
    warnings = []
    if any(PurePosixPath(p).suffix.lower() in {'.js','.mjs'} for p in files):
        warnings.append('JavaScript is preserved in the ZIP download but never executed in previews.')
    if skipped:
        warnings.append(f'{len(skipped)} unsupported file(s) omitted from output: ' + ', '.join(skipped[:5]))
    return SiteBundle(files=files, homepage=homepage, warnings=warnings)


def resolve_local(raw: str | None, current: str, files: dict | None = None) -> str | None:
    """Resolve relative references; never allow remote, absolute or directory traversal."""
    if not raw or not isinstance(raw, str):
        return None
    from urllib.parse import urlsplit, unquote
    raw = raw.strip()
    if raw.startswith(('#', '//', '\\')):
        return None
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    if parts.scheme or parts.netloc:
        return None
    name = unquote(parts.path)
    if not name:
        return current if files is None or current in files else None
    if '\\' in name or '\x00' in name:
        return None
    joined = (posixpath.normpath(name.lstrip('/')) if name.startswith('/')
              else posixpath.normpath(posixpath.join(posixpath.dirname(current), name)))
    if joined == '.' and files is not None:
        return next((p for p in ('index.html','index.htm') if p in files),None)
    if joined in ('.', '..') or joined.startswith('../'):
        return None
    if files is not None and joined not in files:
        # A website sometimes references a directory instead of index.html
        if joined + '/index.html' in files:
            return joined + '/index.html'
        return None
    return joined


def to_zip(bundle: SiteBundle) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6) as archive:
        for name, data in sorted(bundle.files.items()):
            safe_path(name)
            archive.writestr(name, data)
    return output.getvalue()
