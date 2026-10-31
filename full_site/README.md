For the maintained project overview, verification results and current limitations, see [the repository README](../README.md).

# 404 Afterlife — Real Website Modernization (CS/Backend)

This is an **independently testable full-site backend** for the hackathon. It uses original website files, not fabricated content or a generic replacement page.

## What works

- Upload a real ZIP website; validate bounds, reject traversal/symlinks; keep original HTML, CSS, images, SVG, fonts, JS and supported assets as files.
- Parse **all** HTML pages, analyze text/headings/assets/links and CSS colors; report missing local references.
- Show **Before / After for the same selected page**, with the original stylesheet, local image assets (including sanitized SVG) and local fonts. Preview scripts/forms/external requests are disabled. Page selector changes the previewed page.
- Apply a **non-AI CSS modernization layer** to every original page; original HTML and assets remain. Baseline does not invent content. Select `Safe CSS refresh` to demonstrate.
- Export **complete website ZIP**, including every original file and the new CSS. Also export original ZIP for checking.
- Recover a website from a Wayback URL via a bounded same-host crawl (up to **12 HTML pages / 60 assets / 20 MB**) and rewrite recovered local references; report missing files rather than claim complete recovery.
- Team AI integration over a JSON HTTP endpoint or imported JSON; validation limits edits to **existing HTML/CSS**, checks original text and references, preserves binaries.

## Important limitations

- ZIP input can contain all HTML pages; our app handles every HTML page. Only allowed static assets are included; server-side database/PHP/ASP backends are **not recreated**. Original JS is retained for export but **not executed in the preview**. Do not deploy unknown JS without review.
- Archived URL recovery is *best effort*. Old websites can contain thousands of pages or assets archived incompletely; the current crawl has safety limits and does not guarantee a full copy.
- CSS refresh is **NOT AI**. Actual AI needs Rana/Suzy's model or endpoint. Use the imported JSON option to test integration without an endpoint.
- The `components.html` preview uses a restrictive CSP inside the iframe; it is **not a hardened production sandbox**. Public deployments should serve untrusted content from a dedicated isolated origin with proper HTTP CSP and sandbox headers, and use network isolation for archive fetching.
- Analysis of broken links and model preservation are conservative heuristics; test real websites manually.

## Install and run (Windows PowerShell)

```powershell
cd path\to\afterlife\full_site
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If you already have `.venv`, skip the `python -m venv .venv` line.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Use the sample ZIP included in `examples/sample_website_404_afterlife.zip`. Select **Upload ZIP → Safe CSS refresh → Revive Entire Website**. Select **index.html** or **about.html** to compare both pages and download the complete output ZIP.

## Original team project / merge guidance

**Make a new copy or Git branch before replacing any files.** The included `app.py` is an updated UI that uses the `services/site_bundle.py`, `analysis.py`, `preview.py`, `redesign.py`, `ai_bridge.py` and `archive_site.py` modules. It does *not* import the old fallback reconstruction or analyzer. Keep teammates' files safe; merge intentionally rather than replacing their work blindly.

## Team AI contract (Rana / Suzy)

1. Malak exports `404_afterlife_team_ai_input.json` from the app; it includes all original HTML/CSS and an asset manifest.
2. AI engine should modernize the **existing** HTML and CSS across all pages. Avoid invented business information, missing original links, missing images or new JS.
3. Return JSON with **every existing HTML page** (and optional changed CSS files):

```json
{
  "files": {
    "index.html": "<!doctype html><html>...entire revised original homepage...</html>",
    "about.html": "<!doctype html><html>...entire revised original About page...</html>",
    "css/style.css": "body { background: white; }"
  }
}
```

4. Malak selects **Import team AI JSON**, uploads that response and presses Revive, or connects an HTTP API as below.
5. Backend verifies EVERY original HTML page is included, existing paths/content/links and produces a complete ZIP. If validation fails, UI shows the error; it does **not** call the output AI-generated.

### Optional local / HTTPS team API

Configure an endpoint the server administrator trusts, which accepts a POST JSON body and responds with the JSON above:

```powershell
$env:AFTERLIFE_AI_ENDPOINT = "http://127.0.0.1:8000/redesign"
# Optional, if the team service requires it:
$env:AFTERLIFE_AI_API_KEY = "your_api_key"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Use `https://` for a remote team API. No model keys are embedded in source code. **Never submit user websites to an untrusted endpoint.** The service should have timeouts and its own rate limiting/authorization.

## File map

- `app.py`: input selection, full-site workflow, preview selector, ZIP/JSON downloads.
- `services/site_bundle.py`: ZIP security, path resolution, archive output.
- `services/analysis.py`: all-pages analysis and reference checks.
- `services/preview.py`: static CSS/image/font previews with CSP.
- `services/redesign.py`: non-AI, reversible CSS redesign of **all** pages.
- `services/ai_bridge.py`: HTTP/JSON integration with team AI + response validation.
- `services/archive_site.py`: same-host bounded Wayback asset/page recovery.
- `services/security.py`: public URL validation before archive lookup.
- `tests/test_full_website.py`: preservation, preview, security and AI-contract tests.

### Simplest Windows launcher

Double-click `RUN_WINDOWS.bat` from inside the **new project folder**. It creates `.venv` if missing, installs requirements, and starts Streamlit. The launcher is plain text; read it before running.
