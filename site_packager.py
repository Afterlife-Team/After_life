
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZIP_DEFLATED
from io import BytesIO
import json
import posixpath


SOURCE_ZIP = Path("sample_site.zip")
REDESIGNED_DIR = Path("multi_page_output")
RECOVERED_DIR = Path("missing_page_output")
OUTPUT_ZIP = Path("404_afterlife_complete.zip")


def safe_path(name):
    if not isinstance(name, str):
        return None

    if (
        not name
        or "\\" in name
        or "\x00" in name
        or name.startswith("/")
    ):
        return None

    path = PurePosixPath(name)

    if (
        ".." in path.parts
        or ":" in name
        or name.startswith("./")
    ):
        return None

    normalized = posixpath.normpath(name)

    if normalized in (".", ".."):
        return None

    if normalized.startswith("../"):
        return None

    return normalized


def package_site():
    if not SOURCE_ZIP.exists():
        raise FileNotFoundError(SOURCE_ZIP)

    output_files = {}
    copied_assets = []
    redesigned_pages = []
    proposed_pages = []

    # Read safe, limited-size assets from source ZIP.
    MAX_ASSET_BYTES = 10 * 1024 * 1024
    MAX_TOTAL_BYTES = 50 * 1024 * 1024
    total_bytes = 0

    allowed_extensions = {
        ".png", ".jpg", ".jpeg", ".gif",
        ".webp", ".svg", ".css", ".ico"
    }

    with ZipFile(SOURCE_ZIP) as original:
        for info in original.infolist():
            if info.is_dir():
                continue

            name = safe_path(info.filename)

            if name is None:
                continue

            suffix = PurePosixPath(name).suffix.lower()

            if suffix not in allowed_extensions:
                continue

            if info.file_size > MAX_ASSET_BYTES:
                continue

            if total_bytes + info.file_size > MAX_TOTAL_BYTES:
                continue

            # Do not copy links or special Unix files.
            file_type = (info.external_attr >> 16) & 0o170000
            if file_type not in (0, 0o100000):
                continue

            with original.open(info) as source:
                content = source.read(MAX_ASSET_BYTES + 1)

            if len(content) > MAX_ASSET_BYTES:
                continue

            output_files[name] = content
            copied_assets.append(name)
            total_bytes += len(content)

    # Add redesigned HTML pages.
    for path in REDESIGNED_DIR.rglob("*.html"):
        relative = path.relative_to(
            REDESIGNED_DIR
        ).as_posix()

        name = safe_path(relative)

        if name is None:
            continue

        output_files[name] = path.read_bytes()
        redesigned_pages.append(name)

    # Add proposed reconstruction pages.
    for path in RECOVERED_DIR.rglob("*.html"):
        relative = path.relative_to(
            RECOVERED_DIR
        ).as_posix()

        name = safe_path(relative)

        if name is None:
            continue

        # Never overwrite a surviving redesigned page.
        if name in output_files:
            continue

        output_files[name] = path.read_bytes()
        proposed_pages.append(name)

    if not redesigned_pages:
        raise ValueError(
            "No redesigned HTML pages found"
        )

    report = {
        "redesigned_pages": sorted(redesigned_pages),
        "proposed_pages": sorted(proposed_pages),
        "copied_assets": sorted(copied_assets),
        "warning": (
            "Proposed pages are AI-assisted "
            "reconstructions, not recovered originals. "
            "Missing assets cannot be restored unless "
            "the source archive contains them."
        )
    }

    output_files["afterlife_report.json"] = (
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False
        ).encode("utf-8")
    )

    # Build final ZIP in memory, then write once.
    buffer = BytesIO()

    with ZipFile(
        buffer, "w", compression=ZIP_DEFLATED
    ) as archive:
        for name, content in sorted(
            output_files.items()
        ):
            archive.writestr(name, content)

    OUTPUT_ZIP.write_bytes(buffer.getvalue())

    print("ZIP created:", OUTPUT_ZIP)
    print(json.dumps(report, indent=2))

    return report


if __name__ == "__main__":
    package_site()
