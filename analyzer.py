
from bs4 import BeautifulSoup

def extract_content(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    # Extract title
    title = soup.title.get_text(strip=True) if soup.title else "Untitled"

    # Extract headings
    headings = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        headings.append(tag.get_text(" ", strip=True))

    # Extract paragraphs
    paragraphs = []
    for tag in soup.find_all("p"):
        paragraphs.append(tag.get_text(" ", strip=True))

    # Extract links
    links = []
    for tag in soup.find_all("a", href=True):
        links.append({
            "text": tag.get_text(" ", strip=True),
            "href": tag["href"]
        })

    # Extract images
    images = []
    for tag in soup.find_all("img", src=True):
        images.append({
            "src": tag["src"],
            "alt": tag.get("alt", "")
        })

    return {
        "title": title,
        "headings": headings,
        "paragraphs": paragraphs,
        "links": links,
        "images": images
    }

from pathlib import Path
from urllib.parse import urlsplit, unquote


def check_broken_links(site_folder):
    site_root = Path(site_folder).resolve()

    broken_links = []
    missing_images = []

    for html_file in site_root.rglob("*.html"):
        html_content = html_file.read_text(
            encoding="utf-8",
            errors="replace"
        )

        data = extract_content(html_content)

        for link in data["links"]:
            href = link["href"]
            parsed = urlsplit(href)

            if parsed.scheme or parsed.netloc or href.startswith(("#", "//")):
                continue

            target_name = unquote(parsed.path)

            if not target_name:
                continue

            if target_name.startswith("/"):
                target = site_root / target_name.lstrip("/")
            else:
                target = html_file.parent / target_name

            target = target.resolve()

            if not target.is_relative_to(site_root):
                continue

            if target.is_dir():
                target = target / "index.html"

            if not target.is_file():
                broken_links.append({
                    "source": str(html_file.relative_to(site_root)),
                    "target": href
                })

        for img in data["images"]:
            src = img["src"]
            parsed = urlsplit(src)

            if parsed.scheme or parsed.netloc or src.startswith(("//", "#")):
                continue

            target_name = unquote(parsed.path)

            if not target_name:
                continue

            if target_name.startswith("/"):
                target = site_root / target_name.lstrip("/")
            else:
                target = html_file.parent / target_name

            target = target.resolve()

            if not target.is_relative_to(site_root):
                continue

            if not target.is_file():
                missing_images.append({
                    "source": str(html_file.relative_to(site_root)),
                    "target": src
                })

    return {
        "broken_links": broken_links,
        "missing_images": missing_images
    }

from pathlib import Path
from urllib.parse import urlsplit, unquote


def check_broken_links(site_folder):
    site_root = Path(site_folder).resolve()

    broken_links = []
    missing_images = []

    for html_file in site_root.rglob("*.html"):
        html_content = html_file.read_text(
            encoding="utf-8",
            errors="replace"
        )

        data = extract_content(html_content)

        for link in data["links"]:
            href = link["href"]
            parsed = urlsplit(href)

            if parsed.scheme or parsed.netloc or href.startswith(("#", "//")):
                continue

            target_name = unquote(parsed.path)

            if not target_name:
                continue

            if target_name.startswith("/"):
                target = site_root / target_name.lstrip("/")
            else:
                target = html_file.parent / target_name

            target = target.resolve()

            if not target.is_relative_to(site_root):
                continue

            if target.is_dir():
                target = target / "index.html"

            if not target.is_file():
                broken_links.append({
                    "source": str(html_file.relative_to(site_root)),
                    "target": href
                })

        for img in data["images"]:
            src = img["src"]
            parsed = urlsplit(src)

            if parsed.scheme or parsed.netloc or src.startswith(("//", "#")):
                continue

            target_name = unquote(parsed.path)

            if not target_name:
                continue

            if target_name.startswith("/"):
                target = site_root / target_name.lstrip("/")
            else:
                target = html_file.parent / target_name

            target = target.resolve()

            if not target.is_relative_to(site_root):
                continue

            if not target.is_file():
                missing_images.append({
                    "source": str(html_file.relative_to(site_root)),
                    "target": src
                })

    return {
        "broken_links": broken_links,
        "missing_images": missing_images
    }


from zipfile import ZipFile, BadZipFile
from io import BytesIO
from pathlib import PurePosixPath
from urllib.parse import urlsplit, unquote
import posixpath


def analyze_zip(zip_bytes):
    MAX_ZIP_SIZE = 10 * 1024 * 1024
    MAX_TOTAL_SIZE = 30 * 1024 * 1024
    MAX_FILES = 200

    if len(zip_bytes) > MAX_ZIP_SIZE:
        raise ValueError("ZIP file is too large")

    pages = []
    broken_links = []
    missing_images = []

    try:
        with ZipFile(BytesIO(zip_bytes)) as archive:
            files = [item for item in archive.infolist()
                     if not item.is_dir()]

            if len(files) > MAX_FILES:
                raise ValueError("Too many files")

            if sum(item.file_size for item in files) > MAX_TOTAL_SIZE:
                raise ValueError("Uncompressed data too large")

            file_names = set()
            html_files = []

            for item in files:
                name = item.filename.replace("\\", "/")
                parts = PurePosixPath(name).parts

                if (
                    name.startswith("/")
                    or ".." in parts
                    or ":" in name
                    or not name
                ):
                    raise ValueError("Unsafe file path")

                normalized = posixpath.normpath(name)

                if normalized in file_names:
                    raise ValueError("Duplicate file path")

                file_names.add(normalized)

                if normalized.lower().endswith((".html", ".htm")):
                    html_files.append((item, normalized))

            def resolve_target(source, url):
                parsed = urlsplit(url)

                if (
                    parsed.scheme
                    or parsed.netloc
                    or url.startswith(("#", "//"))
                    or not parsed.path
                ):
                    return None

                path = unquote(parsed.path).replace("\\", "/")

                if path.startswith("/"):
                    target = path.lstrip("/")
                else:
                    source_dir = posixpath.dirname(source)
                    target = posixpath.join(source_dir, path)

                target = posixpath.normpath(target)

                if target == ".." or target.startswith("../"):
                    return None

                return target

            for item, name in html_files:
                html = archive.read(item).decode(
                    "utf-8", errors="replace"
                )

                content = extract_content(html)

                pages.append({
                    "path": name,
                    **content
                })

                for link in content["links"]:
                    target = resolve_target(name, link["href"])

                    if target is None:
                        continue

                    if (
                        target not in file_names
                        and posixpath.join(target, "index.html")
                        not in file_names
                    ):
                        broken_links.append({
                            "source": name,
                            "target": link["href"]
                        })

                for img in content["images"]:
                    target = resolve_target(name, img["src"])

                    if target is None:
                        continue

                    if target not in file_names:
                        missing_images.append({
                            "source": name,
                            "target": img["src"]
                        })

    except BadZipFile:
        raise ValueError("Invalid ZIP file")

    return {
        "pages": pages,
        "broken_links": broken_links,
        "missing_assets": missing_images,
        "summary": {
            "total_pages": len(pages),
            "broken_links_count": len(broken_links),
            "missing_assets_count": len(missing_images)
        }
    }


