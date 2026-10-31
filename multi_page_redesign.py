
from pathlib import Path
from html import escape
import json
import posixpath
from urllib.parse import urlsplit, unquote

from analyzer import analyze_zip
from ai_engine import generate_redesign


def prepare_page_data(page, analysis):
    """Convert one analyzed page into AI input."""

    headings = page.get("headings", [])
    paragraphs = page.get("paragraphs", [])

    html_parts = []

    for heading in headings:
        if str(heading).strip():
            html_parts.append(
                f"<h2>{escape(str(heading))}</h2>"
            )

    for paragraph in paragraphs:
        if str(paragraph).strip():
            html_parts.append(
                f"<p>{escape(str(paragraph))}</p>"
            )

    # Temporary support for heading-only pages.
    # The current AI engine requires text sections.
    if not paragraphs and headings:
        html_parts.append(
            f"<p>{escape(str(headings[0]))}</p>"
        )

    page_path = page["path"]
    page_dir = posixpath.dirname(page_path)

    existing = {
        p["path"].replace("\\", "/")
        for p in analysis["pages"]
    }

    missing = {
        str(item.get("target", ""))
        for item in analysis.get("broken_links", [])
    }

    navigation = []

    for link in page.get("links", []):
        href = str(link.get("href", "")).strip()
        label = str(link.get("text", "")).strip()

        if not href or not label or "\\" in href:
            continue

        parsed = urlsplit(href)

        if parsed.scheme or parsed.netloc:
            continue

        path = unquote(parsed.path)

        if not path:
            continue

        if path.startswith("/"):
            target = posixpath.normpath(
                path.lstrip("/")
            )
        else:
            target = posixpath.normpath(
                posixpath.join(page_dir, path)
            )

        if target == ".." or target.startswith("../"):
            continue

        if target in missing:
            status = "missing"
        elif target in existing:
            status = "working"
        else:
            status = "unknown"

        navigation.append({
            "label": label,
            "href": href,
            "status": status
        })

    return {
        "url": None,
        "year": None,
        "content": {
            "title": page.get("title") or page_path,
            "html": "\n".join(html_parts),
            "text": " ".join(
                str(x) for x in headings + paragraphs
            ),
            "navigation": navigation
        },
        "analysis": analysis
    }


def redesign_all_pages(zip_bytes):
    """Redesign every existing HTML page."""

    analysis = analyze_zip(zip_bytes)

    redesigned_pages = {}
    failed_pages = {}

    for page in analysis.get("pages", []):
        path = page["path"]

        print(f"\nRedesigning: {path}")

        website_data = prepare_page_data(
            page, analysis
        )

        result = generate_redesign(website_data)
        print("AI USED:", result.get("ai_used"))
        print("FALLBACK:", result.get("fallback_reason"))

        if result.get("status") == "success":
            redesigned_pages[path] = result["html"]
            print(f"SUCCESS: {path}")
        else:
            failed_pages[path] = result.get(
                "message", "Unknown error"
            )
            print(f"FAILED: {path}")

    return {
        "analysis": analysis,
        "redesigned_pages": redesigned_pages,
        "failed_pages": failed_pages,
        "total_pages": len(analysis.get("pages", []))
    }


if __name__ == "__main__":

    zip_bytes = Path("sample_site.zip").read_bytes()

    results = redesign_all_pages(zip_bytes)

    output_dir = Path("multi_page_output")
    output_dir.mkdir(exist_ok=True)

    for path, html in results["redesigned_pages"].items():
        # Preserve valid relative page paths.
        relative = Path(path.replace("\\", "/"))

        if (
            relative.is_absolute()
            or ".." in relative.parts
            or ":" in path
        ):
            raise ValueError("Unsafe output path")

        destination = output_dir / relative
        destination.parent.mkdir(
            parents=True, exist_ok=True
        )
        destination.write_text(
            html, encoding="utf-8"
        )

    report = {
        "total_pages": results["total_pages"],
        "successful_pages": list(
            results["redesigned_pages"]
        ),
        "failed_pages": results["failed_pages"]
    }

    (output_dir / "report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print("\n=== FINAL RESULTS ===")
    print(json.dumps(report, indent=2))
