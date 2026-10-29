
from html import escape
from pathlib import PurePosixPath
from urllib.parse import urlsplit, unquote
import re


def safe_local_href(href):
    """
    Accept only simple local HTML paths.
    Reject external URLs and dangerous schemes.
    """
    if not isinstance(href, str):
        return None

    href = href.strip()

    if not href or len(href) > 300:
        return None

    if "\\" in href or any(ord(c) < 32 for c in href):
        return None

    parsed = urlsplit(href)

    if parsed.scheme or parsed.netloc:
        return None

    if href.startswith(("/", "//", "#")):
        return None

    if parsed.query or parsed.fragment:
        return None

    path = unquote(parsed.path)

    if not path.lower().endswith((".html", ".htm")):
        return None

    parts = PurePosixPath(path).parts

    if ".." in parts or "." in parts:
        return None

    if not re.fullmatch(
        r"[A-Za-z0-9_./%-]+", href
    ):
        return None

    return href


def render_navigation(navigation):
    if not isinstance(navigation, list):
        return ""

    items = []

    for link in navigation:
        if not isinstance(link, dict):
            continue

        label = escape(str(link.get("label", "")))
        status = link.get("status", "unknown")
        href = safe_local_href(link.get("href", ""))

        if not label:
            continue

        if status == "missing":
            items.append(
                f'<span class="nav-missing">'
                f'{label} — Missing Page</span>'
            )

        elif status == "working" and href:
            # Archive-local paths are intentionally
            # shown as labels in the standalone preview.
            # They may not exist beside the exported HTML.
            items.append(
                f'<span class="nav-item">'
                f'{label}</span>'
            )

        else:
            items.append(
                f'<span class="nav-item">'
                f'{label}</span>'
            )

    if not items:
        return ""

    return (
        '<nav aria-label="Original website navigation">'
        + "\n".join(items)
        + "</nav>"
    )


def render_website(data):
    title = escape(str(
        data.get("title") or "Restored Website"
    ))

    subtitle = escape(str(
        data.get("subtitle") or ""
    ))

    sections = data.get("sections", [])
    navigation = data.get("navigation", [])

    section_html = ""

    for section in sections:
        heading = escape(str(
            section.get("heading", "")
        ))

        text = escape(str(
            section.get("text", "")
        ))

        if not text and not heading:
            continue

        section_html += f"""
<section class="card">
    <h2>{heading}</h2>
    <p>{text}</p>
</section>
"""

    nav_html = render_navigation(navigation)

    subtitle_html = (
        f"<p>{subtitle}</p>"
        if subtitle else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
* {{
    box-sizing: border-box;
}}

body {{
    font-family: Arial, sans-serif;
    background: #f4f6fb;
    margin: 0;
    color: #202638;
    line-height: 1.6;
}}

header {{
    background: #202c59;
    color: white;
    padding: 65px 25px;
    text-align: center;
}}

header h1 {{
    margin: 0;
    font-size: 2.5rem;
}}

header p {{
    color: #e2e8f0;
}}

nav {{
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
    gap: 12px;
    padding: 20px;
    background: white;
}}

.nav-item {{
    background: #e8eefc;
    color: #202c59;
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: bold;
}}

.nav-missing {{
    background: #fff1f2;
    color: #b42335;
    border: 1px solid #fecdd3;
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: bold;
}}

main {{
    max-width: 950px;
    margin: 40px auto;
    padding: 0 20px;
}}

.card {{
    background: white;
    padding: 25px;
    margin-bottom: 20px;
    border-radius: 14px;
    box-shadow: 0 5px 20px #00000012;
}}

.card h2 {{
    margin-top: 0;
    color: #202c59;
}}

@media (max-width: 600px) {{
    header {{
        padding: 35px 15px;
    }}

    header h1 {{
        font-size: 1.8rem;
    }}

    main {{
        margin: 20px auto;
    }}
}}
</style>
</head>
<body>
<header>
    <h1>{title}</h1>
    {subtitle_html}
</header>

{nav_html}

<main>
{section_html}
</main>
</body>
</html>"""
