
from pathlib import Path
from html import escape
from urllib.parse import urlsplit, unquote
from pprint import pprint
import posixpath

from analyzer import analyze_zip
from ai_engine import generate_redesign


# ==========================================
# STEP 1: Read ZIP website
# ==========================================

zip_path = Path("sample_site.zip")

if not zip_path.exists():
    raise FileNotFoundError(
        "sample_site.zip was not found"
    )

zip_bytes = zip_path.read_bytes()


# ==========================================
# STEP 2: Analyze using Rana's code
# ==========================================

analysis = analyze_zip(zip_bytes)

pages = analysis.get("pages", [])

if not pages:
    raise ValueError("No HTML pages found")

print("\n=== ANALYSIS SUMMARY ===")
pprint(analysis.get("summary", {}))


# ==========================================
# STEP 3: Select homepage
# ==========================================

main_page = next(
    (
        page for page in pages
        if posixpath.basename(
            page.get("path", "").replace("\\", "/")
        ).lower() == "index.html"
    ),
    pages[0]
)

page_path = main_page.get("path", "index.html")
page_directory = posixpath.dirname(page_path)

print("\n=== SELECTED PAGE ===")
print(page_path)


# ==========================================
# STEP 4: Prepare headings and paragraphs
# ==========================================

html_parts = []

for heading in main_page.get("headings", []):
    heading = str(heading).strip()

    if heading:
        html_parts.append(
            f"<h2>{escape(heading)}</h2>"
        )

for paragraph in main_page.get("paragraphs", []):
    paragraph = str(paragraph).strip()

    if paragraph:
        html_parts.append(
            f"<p>{escape(paragraph)}</p>"
        )

# IMPORTANT:
# Links are NOT converted into paragraphs.

original_html = "\n".join(html_parts)

original_text = " ".join(
    main_page.get("headings", [])
    + main_page.get("paragraphs", [])
)


# ==========================================
# STEP 5: Prepare navigation separately
# ==========================================

missing_targets = {
    str(item.get("target", ""))
    for item in analysis.get("broken_links", [])
}

existing_paths = {
    str(page.get("path", "")).replace("\\", "/")
    for page in pages
}

navigation = []

for link in main_page.get("links", []):

    label = str(link.get("text", "")).strip()
    href = str(link.get("href", "")).strip()

    if not label or not href:
        continue

    if "\\" in href:
        continue

    parsed = urlsplit(href)

    # Skip external and unsafe links.
    if parsed.scheme or parsed.netloc:
        continue

    if href.startswith("//"):
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
            posixpath.join(page_directory, path)
        )

    if target == ".." or target.startswith("../"):
        continue

    if target in missing_targets:
        status = "missing"

    elif target in existing_paths:
        status = "working"

    else:
        status = "unknown"

    navigation.append({
        "label": label,
        "href": href,
        "status": status
    })


print("\n=== NAVIGATION ===")
pprint(navigation)


# ==========================================
# STEP 6: Prepare website_data for AI
# ==========================================

website_data = {
    "url": None,
    "year": None,

    "content": {
        "title": main_page.get(
            "title", "Old Website"
        ),
        "html": original_html,
        "text": original_text,
        "navigation": navigation
    },

    "analysis": analysis
}


print("\n=== CONTENT SENT TO AI ===")
print(website_data["content"]["html"])

print("\n=== NAVIGATION SENT TO AI ===")
pprint(website_data["content"]["navigation"])


# ==========================================
# STEP 7: Generate redesign
# ==========================================

print("\n=== GENERATING AI REDESIGN ===")

result = generate_redesign(website_data)

print("STATUS:", result["status"])
print("MESSAGE:", result["message"])


# ==========================================
# STEP 8: Save generated HTML
# ==========================================

if result["status"] == "success":

    output_path = Path(
        "integrated_redesign.html"
    )

    output_path.write_text(
        result["html"],
        encoding="utf-8"
    )

    print(
        "\nIntegrated redesign generated successfully!"
    )

    print("Saved to:", output_path)

else:
    print("\nIntegration failed.")
