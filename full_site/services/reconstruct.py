import html
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

MAX_ITEMS = 12

def extract_content(archived_html: str) -> dict:
    """Extract readable text; never execute archived scripts."""
    soup = BeautifulSoup(archived_html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "object", "embed", "form", "svg"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else "Recovered website"
    headings = [x.get_text(" ", strip=True)[:150] for x in soup.select("h1,h2,h3")][:MAX_ITEMS]
    paragraphs = [x.get_text(" ", strip=True)[:500] for x in soup.select("p") if len(x.get_text(" ", strip=True)) > 15][:MAX_ITEMS]
    links = [{"label": a.get_text(" ", strip=True)[:80], "href": a.get("href", "")}
             for a in soup.select("a[href]") if a.get_text(" ", strip=True)][:MAX_ITEMS]
    return {"title": title[:150], "headings": headings, "paragraphs": paragraphs, "links": links}

def build_reconstruction(content: dict, original_url: str, year: str) -> str:
    """Deterministic, safe baseline. This is NOT an AI model."""
    esc = lambda x: html.escape(str(x), quote=True)
    headings = "".join(f"<h2>{esc(h)}</h2>" for h in content["headings"])
    paragraphs = "".join(f"<p>{esc(p)}</p>" for p in content["paragraphs"])
    items = []
    for link in content["links"]:
        href = link["href"].strip()
        parsed = urlparse(href)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            items.append(f'<li><a href="{esc(href)}" rel="noopener noreferrer" target="_blank">{esc(link["label"])}</a></li>')
    links = "<ul>" + "".join(items) + "</ul>" if items else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>{esc(content["title"])}</title>
<style>body{{margin:0;background:#0b1220;color:#e5e7eb;font-family:system-ui,sans-serif;line-height:1.65}}
main{{max-width:850px;margin:55px auto;padding:36px;background:#182438;border-radius:18px}}
h1{{color:#7dd3fc}}h2{{color:#c4b5fd}}a{{color:#67e8f9}}p{{color:#d1d5db}}
small{{color:#fbbf24}}</style></head><body><main>
<small>Archive-based reconstruction · {esc(year)} · Not the original design</small>
<h1>{esc(content["title"])}</h1>{headings}{paragraphs}{links}
<hr><small>Source: {esc(original_url)}. Content may be incomplete.</small>
</main></body></html>"""

def create_fallback(url: str) -> str:
    """Clearly labelled placeholder; never claim to have recovered content."""
    return build_reconstruction(
        {"title": "No archive available", "headings": ["Reconstruction unavailable"],
         "paragraphs": ["No archived copy was found. This is a placeholder, not recovered website content."],
         "links": []}, url, "unknown")
